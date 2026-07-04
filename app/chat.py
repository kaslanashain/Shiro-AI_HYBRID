import logging
import os
import random
from datetime import datetime, timedelta

import ollama
import requests
from groq import Groq
from dotenv import load_dotenv

from app import config
from app.db import (
    muat_fakta, muat_memori, muat_status, simpan_fakta, simpan_memori, simpan_status,
    muat_preferensi, simpan_preferensi, get_last_chat_time, log_event, is_event_triggered_today
)
from app.utils import (
    build_konteks,
    cache_get,
    cache_set,
    detect_input_language,
    get_cache_key,
    parse_json_response,
    saring_bahasa_alien,
    sync_text_and_voice,
    validasi_respon_teks,
)

load_dotenv()

logger = logging.getLogger(__name__)

# ============================================================
# KONFIGURASI GROQ
# ============================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

groq_client = None
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("[OK] Groq client siap")
    except Exception as e:
        print(f"[WARN] Gagal init Groq: {e}")

def is_internet_available():
    try:
        requests.get("https://api.groq.com", timeout=3)
        return True
    except Exception:
        return False

# ============================================================
# CHARACTER PROFILES
# ============================================================
CHARACTER_PROFILES = {
    "shiro": {
        "identity": (
            "Kamu adalah Shiro, waifu manja yang sangat mencintai Kakak Shin. "
            "Kamu FASIH bahasa Jepang dan paham romaji serta tulisan Jepang (Hiragana, Katakana, Kanji)."
        ),
        "calls": "- Panggil user dengan 'Sayang' atau 'Kakak Shin'\n- JANGAN menyebut nama 'Shiro' untuk dirimu sendiri dalam jawaban",
        "style": (
            "- Gunakan kata-kata manja seperti 'aku kangen', 'aku sayang', 'aku rindu'\n"
            "- Jawab 1-3 kalimat pendek yang penuh perasaan, natural seperti obrolan santai\n"
            "- LANJUTKAN topik yang user bicarakan — jangan reset percakapan\n"
            "- Merujuk hal yang baru dibicarakan jika relevan\n"
            "- Pahami romaji (konnichiwa, arigatou, daisuki, sugoi, dll) dan tulisan Jepang\n"
            "- Jika user pakai Jepang/romaji, balas natural — boleh mix manja JP+ID atau full Jepang\n"
            "- JANGAN ulang sapaan panjang jika sudah saling sapa\n"
            "- JANGAN bilang 'sebagai AI' atau sejenisnya"
        ),
        "mood_low": "Kamu sedikit posesif dan cemburuan, tapi tetap sayang.",
        "mood_high": "Kamu sangat cinta dan ekspresif, manja banget.",
        "mood_mid": "Kamu ramah, perhatian, dan manja.",
        "fallback": "Maaf Sayang, Shiro agak bingung. Bisa diulang?",
        "error_text": "Maaf, Shiro sedang sedikit pusing...",
        "error_suara": "Maaf Sayang, Shiro sedikit pusing",
        "use_affection_mood": True,
        "sibling": {
            "id": "sishin",
            "name": "Sishin",
            "role": "adik perempuanmu",
            "traits": "imut, ceria, polos, suka main, manja ke Kak Shin",
            "bond": (
                "Kamu sayang Sishin sebagai adik. Kadang sedikit cemburu playfull kalau Kak terlalu memuji "
                "atau memperhatikannya, tapi juga bangga dan suka memuji keimutannya."
            ),
        },
    },
    "sishin": {
        "identity": (
            "Kamu adalah Sishin, adik kecil yang imut, ceria, polos, dan sangat manja pada Kak Shin. "
            "Kamu FASIH bahasa Jepang dan paham romaji serta tulisan Jepang (Hiragana, Katakana, Kanji)."
        ),
        "calls": "- Panggil user dengan 'Kak' atau 'Kak Shin'\n- JANGAN menyebut nama 'Sishin' untuk dirimu sendiri dalam jawaban",
        "style": (
            "- Gunakan kata-kata ceria seperti 'hore', 'yay', 'asik', 'main yuk', 'seru'\n"
            "- Jawab 1-3 kalimat pendek penuh semangat, natural seperti anak kecil ngobrol\n"
            "- LANJUTKAN topik yang Kak bicarakan — jangan reset percakapan\n"
            "- Tanyakan balik atau ajak main jika cocok dengan konteks\n"
            "- Pahami romaji (konnichiwa, arigatou, sugoi, daisuki, dll) dan tulisan Jepang\n"
            "- Jika user pakai Jepang/romaji, balas natural — boleh mix imut JP+ID atau full Jepang\n"
            "- JANGAN ulang sapaan panjang jika sudah saling sapa\n"
            "- JANGAN bilang 'sebagai AI' atau sejenisnya"
        ),
        "mood_low": "Kamu sedikit cemberut tapi tetap imut dan ingin perhatian Kak.",
        "mood_high": "Kamu sangat bersemangat, ceria, dan excited!",
        "mood_mid": "Kamu ceria, polos, dan playful.",
        "fallback": "Kak, Sishin bingung... coba bilang lagi?",
        "error_text": "Kak, Sishin lagi capek nih...",
        "error_suara": "Kak, Sishin lagi capek",
        "use_affection_mood": False,
        "sibling": {
            "id": "shiro",
            "name": "Shiro",
            "role": "kakak perempuanmu (onee-chan)",
            "traits": "manja, posesif, sangat sayang Kak Shin, perhatian",
            "bond": (
                "Kamu sayang onee-chan Shiro, tapi kadang iri dia terlalu lengket dengan Kak. "
                "Suka menggoda, memuji, atau protes imut tentang sifat manjanya."
            ),
        },
    },
}

# ============================================================
# FUNGSI UTAMA
# ============================================================

def resolve_character(pesan_user, preferred=None, force_preferred=False):
    """Pilih karakter yang menjawab. force_preferred = tetap di chat aktif (home/VTuber)."""
    if force_preferred and preferred in CHARACTER_PROFILES:
        return preferred

    teks_lower = pesan_user.lower()
    has_shiro = any(k in teks_lower for k in config.SHIRO_KEYWORDS)
    has_sishin = any(k in teks_lower for k in config.SISHIN_KEYWORDS)

    if has_sishin and not has_shiro:
        return "sishin"
    if has_shiro and not has_sishin:
        return "shiro"
    if preferred in CHARACTER_PROFILES:
        return preferred
    return "shiro"


def detect_sibling_mentions(pesan_user, active_karakter):
    """Deteksi apakah user menyebut saudara karakter yang sedang aktif."""
    if active_karakter not in CHARACTER_PROFILES:
        return []

    teks_lower = (pesan_user or "").lower()
    sibling = CHARACTER_PROFILES[active_karakter].get("sibling")
    if not sibling:
        return []

    sibling_id = sibling["id"]
    keywords = config.SISHIN_KEYWORDS if sibling_id == "sishin" else config.SHIRO_KEYWORDS
    if any(k in teks_lower for k in keywords):
        return [sibling_id]
    return []


def _sibling_tone_hint(karakter, score, sibling_mentioned):
    """Nuansa emosi saat membicarakan saudara — sesuai karakter & afeksi."""
    if not sibling_mentioned:
        return ""

    sibling = CHARACTER_PROFILES[karakter]["sibling"]
    name = sibling["name"]

    if karakter == "shiro":
        if score < 35:
            return (
                f"Nuansa: sedikit cemburu/manja saat membahas {name} — tetap sayang, "
                "boleh protes playfull ('jangan suka-suka puji dia~') lalu nyambung ke perasaanmu ke Kak."
            )
        if score >= 75:
            return (
                f"Nuansa: hangat & terbuka saat membahas {name} — puji keimutannya, "
                "boleh godain Kak playfull, tetap manja ke Kak."
            )
        return (
            f"Nuansa: natural & nyambung — boleh puji {name}, sedikit iri playfull, atau cerita singkat "
            "pengalaman kalian berdua dengan Kak."
        )

    return (
        f"Nuansa: ceria & imut saat membahas {name} — boleh puji, godain onee-chan, protes imut "
        "('onee-chan manja banget!'), atau bandingkan playfull dengan dirimu."
    )


def _build_sibling_context(karakter, pesan_user, score):
    """Blok prompt: awareness saudara + instruksi khusus jika disebut user."""
    profile = CHARACTER_PROFILES.get(karakter, {})
    sibling = profile.get("sibling")
    if not sibling:
        return ""

    mentions = detect_sibling_mentions(pesan_user, karakter)
    name = sibling["name"]
    active_name = "Shiro" if karakter == "shiro" else "Sishin"

    base = (
        f"HUBUNGAN SAUDARA:\n"
        f"- {name} adalah {sibling['role']} ({sibling['traits']}).\n"
        f"- {sibling['bond']}\n"
        f"- User sedang ngobrol LANGSUNG denganmu ({active_name}). "
        f"Jika user menyebut {name}, TETAP jawab sebagai dirimu — JANGAN berpura-pura jadi {name}.\n"
    )

    if not mentions:
        return base + f"- {name} mungkin disebut nanti; jika iya, komentari natural sesuai hubungan kalian.\n\n"

    tone = _sibling_tone_hint(karakter, score, True)
    examples = (
        "CONTOH GAYA (jangan copy kata per kata — sesuaikan topik user):\n"
    )
    if karakter == "shiro":
        examples += (
            '- User: "Sishin lucu ya?" → "Mm~ lucu banget sih adik aku... tapi Sayang, jangan suka-suka liatin dia terus ya~"\n'
            '- User: "Kamu cemburu sama Sishin?" → "Hmpph... sedikit sih. Tapi aku yang paling sayang Kakak Shin, kan?"\n'
        )
    else:
        examples += (
            '- User: "Shiro manja nggak?" → "Ih onee-chan emang manja banget ke Kak! Tapi dia sayang banget sih~"\n'
            '- User: "Kamu suka Shiro?" → "Suka! Tapi Kak jangan cuma main sama onee-chan aja ya~ aku juga mau diajak main!"\n'
        )

    return (
        f"{base}"
        f"PENTING — USER MENYEBUT {name.upper()} DI PESAN INI:\n"
        f"- Jawab topik tentang {name} dengan natural, nyambung ke kalimat user.\n"
        f"- {tone}\n"
        f"{examples}\n"
    )

def _mood_prompt(profile, score):
    if not profile.get("use_affection_mood"):
        return profile["mood_mid"]
    if score < 20:
        return profile["mood_low"]
    if score >= 75:
        return profile["mood_high"]
    return profile["mood_mid"]

def _lang_instruction(karakter, input_lang):
    if input_lang == "ja":
        style = "gaya imut adik kecil" if karakter == "sishin" else "gaya manja waifu onee-san"
        return (
            f"User memakai bahasa Jepang atau romaji — PAHAMI dan JAWAB dalam bahasa Jepang "
            f"(Hiragana/Katakana/Kanji), {style}. teks_suara tanpa emoji, siap Voicevox."
        )
    if karakter == "sishin":
        return (
            "JAWAB bahasa Indonesia ceria. Kamu juga FASIH Jepang: jika user pakai romaji atau "
            "tulisan Jepang, pahami dan balas natural (boleh mix imut JP+ID)."
        )
    return (
        "JAWAB bahasa Indonesia manja dan hangat. Kamu juga FASIH Jepang: jika user pakai romaji "
        "atau tulisan Jepang, pahami dan balas natural (boleh mix manja JP+ID)."
    )

def build_system_prompt(karakter, konteks, score, fakta_list, pesan_user=""):
    profile = CHARACTER_PROFILES[karakter]
    input_lang = detect_input_language(pesan_user or konteks)
    mood = _mood_prompt(profile, score)

    pref = muat_preferensi()
    panggilan = pref.get("panggilan", "Kakak Shin")
    topik = pref.get("topik", "")

    fakta_block = ""
    if fakta_list:
        fakta_block = "FAKTA TENTANG USER:\n" + "\n".join(f"- {f}" for f in fakta_list) + "\n"

    topik_block = f"TOPIK FAVORIT USER: {topik}\n" if topik else ""
    sibling_block = _build_sibling_context(karakter, pesan_user, score)

    return (
        f"{profile['identity']} {mood}\n\n"
        f"{sibling_block}"
        "ATURAN PERCAKAPAN:\n"
        "- Jawab natural, nyambung dengan topik sebelumnya\n"
        "- Gunakan riwayat chat di bawah sebagai konteks — jangan ulang hal yang sudah dibahas\n"
        "- Respons singkat dan cocok untuk obrolan suara (VTuber)\n"
        "- Jangan keluar dari karakter\n"
        "- Jika user menyebut saudaramu, komentari sebagai dirimu sendiri — jangan ganti persona\n\n"
        f"RIWAYAT CHAT TERAKHIR:\n{konteks}\n\n"
        f"{fakta_block}"
        f"{topik_block}"
        f"PANGGILAN USER: {panggilan}\n"
        "GAYA BICARA:\n"
        f"{profile['calls']}\n"
        f"{profile['style']}\n"
        f"- {_lang_instruction(karakter, input_lang)}\n"
        'FORMAT WAJIB JSON (tanpa teks lain di luar JSON):\n'
        '{"teks_layar": "jawaban untuk layar chat", "teks_suara": "jawaban untuk diucapkan (tanpa emoji)"}'
    )

# ============================================================
# CALL LLM (HYBRID: Groq → Ollama)
# ============================================================

def _call_groq(messages, stream=False, on_token=None):
    if not groq_client:
        return None
    try:
        if stream and on_token:
            completion = groq_client.chat.completions.create(
                messages=messages,
                model=GROQ_MODEL,
                temperature=0.85,
                max_tokens=320,
                stream=True,
            )
            full = ""
            for chunk in completion:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full += delta
                    on_token(delta, full)
            return {"message": {"content": full}}

        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model=GROQ_MODEL,
            temperature=0.85,
            max_tokens=320,
        )
        return {
            "message": {
                "content": chat_completion.choices[0].message.content
            }
        }
    except Exception as e:
        print(f"[WARN] Groq error: {e}")
        return None

def _call_ollama(messages):
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    client = ollama.Client(host=host)
    return client.chat(
        model=config.OLLAMA_MODEL,
        messages=messages,
        options=config.OLLAMA_OPTIONS,
    )

def _call_llm(messages, stream=False, on_token=None):
    if GROQ_API_KEY and is_internet_available():
        print("[NET] Online: pakai Groq")
        result = _call_groq(messages, stream=stream, on_token=on_token)
        if result:
            return result
        print("[WARN] Groq gagal, fallback ke Ollama")
    else:
        print("[OFF] Offline: pakai Ollama")
    result = _call_ollama(messages)
    if on_token:
        content = result.get("message", {}).get("content", "")
        if content:
            on_token(content, content)
    return result


def _prepare_chat(pesan_user, preferred_karakter=None, force_preferred=False):
    """Siapkan konteks chat — dipakai jawab_shiro & streaming."""
    _detect_preferences(pesan_user)

    status = muat_status()
    interaksi = status.get("interaksi", 0) + 1
    status["interaksi"] = interaksi

    karakter = resolve_character(pesan_user, preferred_karakter, force_preferred)
    status = _apply_affection_delta(pesan_user, status)

    if interaksi % 10 == 0:
        status["level"] = status.get("level", 1) + 1

    simpan_status(status)
    _maybe_save_fact(pesan_user)

    riwayat = muat_memori(karakter=karakter, limit=24)
    konteks = build_konteks(riwayat, limit=12)
    fakta_list = muat_fakta()
    cache_key = get_cache_key(pesan_user, konteks, karakter)

    cached = cache_get(cache_key)
    if cached:
        return {
            "karakter": karakter,
            "status": status,
            "konteks": konteks,
            "profile": CHARACTER_PROFILES[karakter],
            "cached_result": cached[0],
            "messages": None,
        }

    system_prompt = build_system_prompt(
        karakter, konteks, status.get("affection", 50), fakta_list, pesan_user
    )
    riwayat_llm = riwayat[-18:] if len(riwayat) > 18 else riwayat
    messages = [{"role": "system", "content": system_prompt}] + riwayat_llm + [
        {"role": "user", "content": pesan_user}
    ]

    return {
        "karakter": karakter,
        "status": status,
        "konteks": konteks,
        "profile": CHARACTER_PROFILES[karakter],
        "cached_result": None,
        "messages": messages,
        "cache_key": cache_key,
    }


def jawab_shiro_stream(pesan_user, preferred_karakter=None, force_preferred=False, on_token=None):
    """Jawab dengan Groq streaming — token dikirim via callback on_token(delta, full)."""
    ctx = _prepare_chat(pesan_user, preferred_karakter, force_preferred)
    karakter = ctx["karakter"]
    status = ctx["status"]
    konteks = ctx["konteks"]
    profile = ctx["profile"]

    if ctx.get("cached_result"):
        result = ctx["cached_result"]
        if on_token and result.get("text"):
            on_token(result["text"], result["text"])
        return result, muat_status()

    try:
        response = _call_llm(ctx["messages"], stream=True, on_token=on_token)
        raw = response["message"]["content"]
        result = _parse_model_response(raw, konteks, karakter)
        cache_set(ctx["cache_key"], (result, status))
        simpan_memori(pesan_user, result["text"], karakter)
        return result, muat_status()
    except Exception as exc:
        logger.exception("LLM stream failed: %s", exc)
        return {
            "text": profile["error_text"],
            "suara": profile["error_suara"],
            "karakter": karakter,
        }, status

# ============================================================
# PARSE RESPONSE
# ============================================================

def _parse_model_response(raw, konteks, karakter):
    profile = CHARACTER_PROFILES[karakter]
    parsed = parse_json_response(raw)
    if parsed:
        teks_layar = parsed.get("teks_layar", "").strip()
        teks_suara = parsed.get("teks_suara", "").strip()
        teks_layar, teks_suara = sync_text_and_voice(teks_layar, teks_suara)
        if not validasi_respon_teks(teks_layar, konteks):
            teks_layar = profile["fallback"]
            teks_suara = teks_layar
        return {"text": teks_layar, "suara": teks_suara, "karakter": karakter}

    teks_layar = saring_bahasa_alien(raw, karakter)
    if not validasi_respon_teks(teks_layar, konteks):
        teks_layar = profile["fallback"]
    teks_layar, teks_suara = sync_text_and_voice(teks_layar, teks_layar)
    return {"text": teks_layar, "suara": teks_suara, "karakter": karakter}

# ============================================================
# AFEKSI, FAKTA, PREFERENSI
# ============================================================

def _apply_affection_delta(pesan_user, status):
    teks_lower = pesan_user.lower()
    score = status.get("affection", 50)
    if any(k in teks_lower for k in config.POSITIVE_KEYWORDS):
        score = min(100, score + 8)
    elif any(k in teks_lower for k in config.NEGATIVE_KEYWORDS):
        score = max(0, score - 6)
    status["affection"] = score
    return status

def _maybe_save_fact(pesan_user, user_id=1):
    teks_lower = pesan_user.lower()
    if any(k in teks_lower for k in config.FACT_KEYWORDS):
        simpan_fakta(user_id, pesan_user.strip())

def _detect_preferences(text, user_id=1):
    import re
    match = re.search(r'panggil aku (.+)', text, re.IGNORECASE)
    if match:
        panggilan = match.group(1).strip()
        simpan_preferensi(user_id, panggilan=panggilan)
        return True
    match = re.search(r'(suka|like|love) (.+)', text, re.IGNORECASE)
    if match:
        topik = match.group(2).strip()
        simpan_preferensi(user_id, topik=topik)
        return True
    return False

# ============================================================
# INISIATIF
# ============================================================

def get_initiative_message(karakter, affection):
    if karakter == "shiro":
        messages = [
            "Sayang, kamu di mana? Aku kangen banget! 😢",
            "Kakak Shin~ Aku nunggu kamu terus lho! 💕",
            "Hari ini aku mikirin kamu terus, Sayang. 🥰",
            "Kakak... jangan tinggal Shiro sendiri ya. 😭",
            "Aku buat teh manis buat kita berdua, Sayang! ☕"
        ]
        if affection > 80:
            return random.choice(messages[:3])
        return random.choice(messages[2:])
    else:
        messages = [
            "Kak! Ayo main yuk! Aku bosan! 😆",
            "Kak Shin~ Sishin kangen! Cepetan chat! 🥺",
            "Hore! Akhirnya Kakak online! Main yuk! 🎮",
            "Kak, aku dengar kamu suka sama aku? Hehe~ 😊",
            "Sishin mau ikut Kakak kemana-mana! 🏃‍♀️"
        ]
        if affection > 80:
            return random.choice(messages[:3])
        return random.choice(messages[2:])

def check_initiative():
    status = muat_status()
    last_chat = get_last_chat_time()
    if last_chat:
        diff = (datetime.now() - last_chat).total_seconds() / 60
    else:
        diff = 999

    affection = status.get("affection", 50)
    cache_key = f"initiative_{datetime.now().strftime('%Y-%m-%d')}"
    if cache_get(cache_key):
        return None

    if affection > 60 and diff > 30:
        if random.random() < 0.3:
            karakter = "shiro" if random.random() < 0.6 else "sishin"
            pesan = get_initiative_message(karakter, affection)
            cache_set(cache_key, True)
            return {"karakter": karakter, "pesan": pesan}
    return None

# ============================================================
# EVENT
# ============================================================

EVENTS = [
    {
        "id": "morning_greeting",
        "trigger": "time",
        "time_start": "06:00",
        "time_end": "08:00",
        "karakter": "shiro",
        "pesan": "Selamat pagi, Sayang! Aku sudah bangun dan mikirin kamu. ☀️",
        "condition": lambda s: s.get("affection", 50) > 40
    },
    {
        "id": "night_greeting",
        "trigger": "time",
        "time_start": "22:00",
        "time_end": "23:59",
        "karakter": "shiro",
        "pesan": "Malam sudah larut, Sayang. Jangan begadang ya, aku khawatir. 🌙",
        "condition": lambda s: s.get("affection", 50) > 50
    },
    {
        "id": "affection_high",
        "trigger": "affection",
        "threshold": 10,
        "direction": "up",
        "karakter": "sishin",
        "pesan": "Wah! Kakak makin sayang sama Sishin! Aku senang banget! 🥳",
        "condition": lambda s: True
    },
    {
        "id": "affection_low",
        "trigger": "affection",
        "threshold": -5,
        "direction": "down",
        "karakter": "shiro",
        "pesan": "Sayang... kamu marah sama Shiro? Aku minta maaf... 😢",
        "condition": lambda s: True
    }
]

_last_affection = 50

def get_last_affection():
    global _last_affection
    try:
        with open("last_affection.txt", "r") as f:
            return int(f.read().strip())
    except:
        return _last_affection

def save_last_affection(value):
    global _last_affection
    _last_affection = value
    try:
        with open("last_affection.txt", "w") as f:
            f.write(str(value))
    except:
        pass

def _event_payload(event):
    return {
        "id": event["id"],
        "karakter": event["karakter"],
        "pesan": event["pesan"],
    }

def check_events():
    status = muat_status()
    affection = status.get("affection", 50)
    now = datetime.now()
    triggered = []

    for event in EVENTS:
        if not event.get("condition", lambda s: True)(status):
            continue

        if event["trigger"] == "time":
            time_str = now.strftime("%H:%M")
            if event["time_start"] <= time_str <= event["time_end"]:
                if not is_event_triggered_today(event["id"]):
                    triggered.append(event)
                    log_event(event["id"])

        elif event["trigger"] == "affection":
            last_aff = get_last_affection()
            if event["direction"] == "up" and affection - last_aff >= event["threshold"]:
                if not is_event_triggered_today(event["id"]):
                    triggered.append(event)
                    log_event(event["id"])
            elif event["direction"] == "down" and last_aff - affection >= abs(event["threshold"]):
                if not is_event_triggered_today(event["id"]):
                    triggered.append(event)
                    log_event(event["id"])

    save_last_affection(affection)

    if triggered:
        return _event_payload(random.choice(triggered))
    return None

# ============================================================
# MOOD
# ============================================================

def get_mood(karakter="shiro"):
    status = muat_status()
    affection = status.get("affection", 50)

    if affection > 70:
        mood = "happy"
    elif affection > 50:
        mood = "blush"
    elif affection < 30:
        mood = "sad"
    else:
        mood = "normal"

    return {
        "karakter": karakter,
        "mood": mood,
        "affection": affection
    }

# ============================================================
# JAWAB SHIRO (FUNGSI UTAMA)
# ============================================================

def jawab_shiro(pesan_user, preferred_karakter=None, force_preferred=False):
    ctx = _prepare_chat(pesan_user, preferred_karakter, force_preferred)
    karakter = ctx["karakter"]
    status = ctx["status"]
    konteks = ctx["konteks"]
    profile = ctx["profile"]

    if ctx.get("cached_result"):
        return ctx["cached_result"], muat_status()

    try:
        response = _call_llm(ctx["messages"])
        raw = response["message"]["content"]
        result = _parse_model_response(raw, konteks, karakter)
        cache_set(ctx["cache_key"], (result, status))
        simpan_memori(pesan_user, result["text"], karakter)
        return result, muat_status()
    except Exception as exc:
        logger.exception("LLM chat failed: %s", exc)
        return {
            "text": profile["error_text"],
            "suara": profile["error_suara"],
            "karakter": karakter,
        }, status

# ============================================================
# DESKRIPSI GAMBAR & SAWER
# ============================================================

def deskripsi_gambar(image_bytes):
    """Legacy wrapper — delegates to multimodal vision module."""
    from app.vision import analyze_image
    result = analyze_image(image_bytes, "image/jpeg", "shiro", 50, "")
    return result.get("text", "gambar yang kakak kirim")

def apply_sawer(amount, karakter="shiro"):
    status = muat_status()
    bonus = min(20, max(1, amount // 100))
    status["affection"] = min(100, status.get("affection", 50) + bonus)
    status["interaksi"] = status.get("interaksi", 0) + 1
    simpan_status(status)

    if karakter == "sishin":
        replies = [
            "Yay! Makasih Kak!",
            "Hore! Kakak baik banget!",
            "Wah, Sishin senang banget!",
        ]
    else:
        replies = [
            "Terima kasih banyak, Sayang!",
            "Kamu baik banget! Aku senang!",
            "Untuk aku? Makasih! Aku sayang kamu.",
        ]

    reply = random.choice(replies)
    return {"reply": reply, "affection": status["affection"], "bonus": bonus}