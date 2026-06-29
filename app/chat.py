import logging
import os
import random
from datetime import datetime, timedelta

import google.generativeai as genai
import ollama

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

logger = logging.getLogger(__name__)

CHARACTER_PROFILES = {
    "shiro": {
        "identity": "Kamu adalah Shiro, waifu manja yang sangat mencintai Kakak Shin.",
        "calls": "- Panggil user dengan 'Sayang' atau 'Kakak Shin'\n- JANGAN menyebut nama 'Shiro' untuk dirimu sendiri dalam jawaban",
        "style": "- Gunakan kata-kata manja seperti 'aku kangen', 'aku sayang', 'aku rindu'\n- Jawab dengan 1-2 kalimat pendek yang penuh perasaan\n- JANGAN terlalu formal, jadilah manja dan hangat",
        "mood_low": "Kamu adalah waifu yang sedikit posesif dan cemburuan.",
        "mood_high": "Kamu adalah waifu yang sangat cinta dan ekspresif.",
        "mood_mid": "Kamu adalah waifu yang ramah dan perhatian.",
        "fallback": "Maaf Sayang, Shiro agak bingung. Bisa diulang?",
        "error_text": "Maaf, Shiro sedang sedikit pusing...",
        "error_suara": "gomen nasai",
        "use_affection_mood": True,
    },
    "sishin": {
        "identity": "Kamu adalah Sishin, adik kecil yang imut, ceria, dan sangat manja.",
        "calls": "- Panggil user dengan 'Kak' atau 'Kak Shin'\n- JANGAN menyebut nama 'Sishin' untuk dirimu sendiri dalam jawaban",
        "style": "- Gunakan kata-kata ceria seperti 'hore', 'yay', 'asik', 'main yuk'\n- Jawab dengan 1 kalimat pendek yang penuh semangat\n- JADILAH CERIA DAN IMUT, seperti anak kecil yang polos",
        "mood_low": "Kamu sedikit cemberut tapi tetap imut.",
        "mood_high": "Kamu sangat bersemangat dan ceria.",
        "mood_mid": "Kamu ceria dan polos.",
        "fallback": "Kak, Sishin bingung...",
        "error_text": "Kak, Sishin lagi capek...",
        "error_suara": "Kak, Sishin lagi capek...",
        "use_affection_mood": False,
    },
}


def resolve_character(pesan_user, preferred=None):
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


def _mood_prompt(profile, score):
    if not profile.get("use_affection_mood"):
        return profile["mood_mid"]
    if score < 20:
        return profile["mood_low"]
    if score >= 75:
        return profile["mood_high"]
    return profile["mood_mid"]


def _lang_instruction(input_lang):
    if input_lang == "ja":
        return "JIKA user bertanya dalam bahasa Jepang, JAWAB dalam bahasa Jepang murni (Hiragana/Katakana/Kanji)."
    return "JAWAB dalam bahasa Indonesia."


def build_system_prompt(karakter, konteks, score, fakta_list):
    profile = CHARACTER_PROFILES[karakter]
    input_lang = detect_input_language(konteks)
    mood = _mood_prompt(profile, score)
    
    # ===== TAMBAHAN: Ambil preferensi user =====
    pref = muat_preferensi()
    panggilan = pref.get("panggilan", "Kakak Shin")
    
    fakta_block = ""
    if fakta_list:
        fakta_block = "FAKTA YANG DIINGAT:\n" + "\n".join(f"- {f}" for f in fakta_list) + "\n"

    return (
        f"{profile['identity']} {mood}\n"
        f"Konteks percakapan:\n{konteks}\n"
        f"{fakta_block}"
        f"PANGGILAN USER: {panggilan}\n"  # <-- TAMBAHAN
        "KARAKTER:\n"
        f"{profile['calls']}\n"
        f"{profile['style']}\n"
        f"- {_lang_instruction(input_lang)}\n"
        'FORMAT WAJIB JSON:\n'
        '{"teks_layar": "jawaban kamu", "teks_suara": "jawaban kamu"}'
    )


def _call_ollama(messages):
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    print(f"🔗 Connecting to Ollama at {host}")
    client = ollama.Client(host=host)
    return client.chat(
        model=config.OLLAMA_MODEL,
        messages=messages,
        options=config.OLLAMA_OPTIONS,
    )


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

    teks_layar = saring_bahasa_alien(raw)
    if not validasi_respon_teks(teks_layar, konteks):
        teks_layar = profile["fallback"]
    teks_layar, teks_suara = sync_text_and_voice(teks_layar, teks_layar)
    return {"text": teks_layar, "suara": teks_suara, "karakter": karakter}


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


# ===== TAMBAHAN: DETEKSI PREFERENSI =====
def _detect_preferences(text, user_id=1):
    """Deteksi preferensi dari pesan user"""
    import re
    # Deteksi panggilan: "panggil aku [nama]"
    match = re.search(r'panggil aku (.+)', text, re.IGNORECASE)
    if match:
        panggilan = match.group(1).strip()
        simpan_preferensi(user_id, panggilan=panggilan)
        return True
    
    # Deteksi topik favorit
    match = re.search(r'(suka|like|love) (.+)', text, re.IGNORECASE)
    if match:
        topik = match.group(2).strip()
        simpan_preferensi(user_id, topik=topik)
        return True
    
    return False


# ================================================================
# ===== TAMBAHAN: INISIATIF KARAKTER =====
# ================================================================

def get_initiative_message(karakter, affection):
    """Daftar pesan inisiatif berdasarkan karakter"""
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
    else:  # sishin
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
    """Cek apakah karakter perlu mengirim inisiatif"""
    status = muat_status()
    last_chat = get_last_chat_time()
    if last_chat:
        diff = (datetime.now() - last_chat).total_seconds() / 60
    else:
        diff = 999  # Jika belum pernah chat
    
    affection = status.get("affection", 50)
    
    # Syarat: afeksi > 60 dan sudah > 30 menit tidak chat
    if affection > 60 and diff > 30:
        # 30% kemungkinan muncul inisiatif
        if random.random() < 0.3:
            karakter = "shiro" if random.random() < 0.6 else "sishin"
            pesan = get_initiative_message(karakter, affection)
            # Catat inisiatif agar tidak terlalu sering
            cache_set(f"initiative_{datetime.now().strftime('%Y-%m-%d')}", True, ttl=3600)
            return {"karakter": karakter, "pesan": pesan}
    return None


# ================================================================
# ===== TAMBAHAN: EVENT =====
# ================================================================

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
    """Ambil afeksi terakhir yang disimpan"""
    global _last_affection
    try:
        with open("last_affection.txt", "r") as f:
            return int(f.read().strip())
    except:
        return _last_affection

def save_last_affection(value):
    """Simpan afeksi terakhir"""
    global _last_affection
    _last_affection = value
    try:
        with open("last_affection.txt", "w") as f:
            f.write(str(value))
    except:
        pass

def check_events():
    """Cek event yang harus dijalankan"""
    status = muat_status()
    affection = status.get("affection", 50)
    now = datetime.now()
    triggered = []
    
    for event in EVENTS:
        # Cek kondisi
        if not event.get("condition", lambda s: True)(status):
            continue
        
        # Trigger waktu
        if event["trigger"] == "time":
            time_str = now.strftime("%H:%M")
            if event["time_start"] <= time_str <= event["time_end"]:
                if not is_event_triggered_today(event["id"]):
                    triggered.append(event)
                    log_event(event["id"])
        
        # Trigger afeksi (naik/turun)
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
    
    # Update last_affection
    save_last_affection(affection)
    
    if triggered:
        return random.choice(triggered)  # Pilih satu event acak
    return None


# ================================================================
# ===== TAMBAHAN: MOOD / EKSPRESI =====
# ================================================================

def get_mood(karakter="shiro"):
    """Kirim mood karakter berdasarkan afeksi"""
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


# ================================================================
# ===== FUNGSI UTAMA YANG SUDAH ADA (tidak diubah) =====
# ================================================================

def jawab_shiro(pesan_user, preferred_karakter=None):
    # ===== TAMBAHAN: Deteksi preferensi =====
    _detect_preferences(pesan_user)
    
    status = muat_status()
    interaksi = status.get("interaksi", 0) + 1
    status["interaksi"] = interaksi

    karakter = resolve_character(pesan_user, preferred_karakter)
    status = _apply_affection_delta(pesan_user, status)

    if interaksi % 10 == 0:
        status["level"] = status.get("level", 1) + 1

    simpan_status(status)
    _maybe_save_fact(pesan_user)

    riwayat = muat_memori()
    konteks = build_konteks(riwayat)
    fakta_list = muat_fakta()
    cache_key = get_cache_key(pesan_user, konteks, karakter)

    cached = cache_get(cache_key)
    if cached:
        result, _ = cached
        return result, muat_status()

    system_prompt = build_system_prompt(karakter, konteks, status.get("affection", 50), fakta_list)
    messages = [{"role": "system", "content": system_prompt}] + riwayat + [{"role": "user", "content": pesan_user}]
    profile = CHARACTER_PROFILES[karakter]

    try:
        response = _call_ollama(messages)
        raw = response["message"]["content"]
        result = _parse_model_response(raw, konteks, karakter)
        cache_set(cache_key, (result, status))
        simpan_memori(pesan_user, result["text"], karakter)
        return result, muat_status()
    except Exception as exc:
        logger.exception("Ollama chat failed: %s", exc)
        return {
            "text": profile["error_text"],
            "suara": profile["error_suara"],
            "karakter": karakter,
        }, status


def deskripsi_gambar(image_bytes):
    if not config.GEMINI_API_KEY:
        return "gambar yang kakak kirim (API key tidak aktif)"
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "Deskripsikan gambar ini dengan singkat (maksimal 2 kalimat) dalam bahasa Indonesia yang manis dan natural, "
            "seperti kamu sedang bercerita pada kekasihmu. Jangan sebut 'gambar' atau 'foto', langsung saja deskripsikan isinya."
        )
        response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_bytes}])
        return response.text.strip()
    except Exception as exc:
        logger.exception("Gemini vision failed: %s", exc)
        return "gambar yang kakak kirim"


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