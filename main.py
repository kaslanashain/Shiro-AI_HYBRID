import os
import sys
import json
import re
import datetime
import time
import threading
import asyncio
import uuid
import subprocess
import io
import sqlite3
from flask import Flask, request, jsonify, render_template, send_file
from dotenv import load_dotenv
import ollama
import edge_tts
import google.generativeai as genai
from PIL import Image

# ===== LOAD ENVIRONMENT VARIABLES =====
load_dotenv()

# ===== SETUP BASE DIRECTORY =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "modules"))

# ===== IMPOR UNTUK SISHIN (TSUKUYOMI-CHAN) =====
import soundfile as sf

try:
    from ezttsModel import ezttsModel as EzttsModel
    print("[Sishin] ezttsModel berhasil diimport!")
    ezttsModel = EzttsModel
except ImportError as e:
    print(f"[Sishin] Gagal import ezttsModel: {e}")
    ezttsModel = None

app = Flask(__name__)

# ===== TEMPORARY DIRECTORY =====
TEMP_DIR = os.path.join(BASE_DIR, "tmp")
os.makedirs(TEMP_DIR, exist_ok=True)

# ===== KONFIGURASI DATABASE SQLITE =====
DB_PATH = os.path.join(BASE_DIR, "Shiro_Sishin.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT DEFAULT 'Kakak Shin',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS memori (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                karakter TEXT DEFAULT 'shiro',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS status (
                user_id INTEGER PRIMARY KEY DEFAULT 1,
                affection INTEGER DEFAULT 50,
                level INTEGER DEFAULT 1,
                interaksi INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS fakta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                fakta TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            INSERT OR IGNORE INTO users (id, nama) VALUES (1, 'Kakak Shin');
            INSERT OR IGNORE INTO status (user_id, affection, level, interaksi) 
            VALUES (1, 50, 1, 0);
        ''')
        print("[Database] ✅ Tabel dan data awal berhasil dibuat!")

init_db()

# ===== FUNGSI MEMORI (SQLite) =====
def muat_memori(user_id=1, limit=30):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM memori WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

def simpan_memori(user, shiro, karakter="shiro", user_id=1):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO memori (user_id, role, content, karakter) VALUES (?, ?, ?, ?)",
            (user_id, 'user', user, karakter)
        )
        conn.execute(
            "INSERT INTO memori (user_id, role, content, karakter) VALUES (?, ?, ?, ?)",
            (user_id, 'assistant', shiro, karakter)
        )
        conn.execute('''
            DELETE FROM memori 
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM memori WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50
            )
        ''', (user_id, user_id))

# ===== FUNGSI STATUS (SQLite) =====
def muat_status(user_id=1):
    with get_db() as conn:
        row = conn.execute(
            "SELECT affection, level, interaksi FROM status WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if row:
            return {"affection": row["affection"], "level": row["level"], "interaksi": row["interaksi"]}
        return {"affection": 50, "level": 1, "interaksi": 0}

def simpan_status(status, user_id=1):
    with get_db() as conn:
        conn.execute(
            "UPDATE status SET affection = ?, level = ?, interaksi = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (status["affection"], status["level"], status["interaksi"], user_id)
        )

# ===== FUNGSI FAKTA (SQLite) =====
def muat_fakta(user_id=1):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT fakta FROM fakta WHERE user_id = ?",
            (user_id,)
        ).fetchall()
        return [row["fakta"] for row in rows]

def simpan_fakta(user_id, fakta):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO fakta (user_id, fakta) VALUES (?, ?)",
            (user_id, fakta)
        )

# ===== KONFIGURASI GEMINI =====
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    print("[Gemini] API Key ditemukan, fitur gambar aktif.")
else:
    print("[Gemini] API Key tidak ditemukan. Fitur gambar tidak akan berfungsi.")

# ===== KONFIGURASI TSUKUYOMI-CHAN =====
TSUKUYOMI_PATH = os.path.join(BASE_DIR, "voice_sishin", "tsukuyomi-chan vits")
CONFIG_PATH = os.path.join(TSUKUYOMI_PATH, "config.json")

TSUKUYOMI_AVAILABLE = False
if ezttsModel is not None and os.path.exists(CONFIG_PATH):
    try:
        test_model = ezttsModel(CONFIG_PATH)
        TSUKUYOMI_AVAILABLE = True
        print("[Sishin] Model Tsukuyomi-chan ditemukan dan siap digunakan!")
    except Exception as e:
        print(f"[Sishin] Model Tsukuyomi-chan gagal dimuat: {e}")
else:
    if not os.path.exists(CONFIG_PATH):
        print(f"[Sishin] Config tidak ditemukan di: {CONFIG_PATH}")
    if ezttsModel is None:
        print("[Sishin] ezttsModel tidak tersedia.")

# ===== KONFIGURASI RVC =====
HAREM_AI = {
    "Miku": {
        "model": os.path.join(BASE_DIR, "voice_shiro", "Miku", "Miku.pth"),
        "index": os.path.join(BASE_DIR, "voice_shiro", "Miku", "Miku.index")
    },
    "Kurumi": {
        "model": os.path.join(BASE_DIR, "voice_shiro", "Kurumi", "Kurumi.pth"),
        "index": os.path.join(BASE_DIR, "voice_shiro", "Kurumi", "Kurumi.index")
    },
    "Origami": {
        "model": os.path.join(BASE_DIR, "voice_shiro", "Origami", "Origami.pth"),
        "index": os.path.join(BASE_DIR, "voice_shiro", "Origami", "Origami.index")
    }
}

# ===== FUNGSI FILTER =====
def saring_bahasa_alien(teks, konteks_sapaan=False):
    teks_clean = str(teks).strip()
    teks_clean = teks_clean.replace('*', '').replace('_', '').replace('"', '').replace('`', '')
    teks_clean = re.sub(r'^shiro:\s*', '', teks_clean, flags=re.IGNORECASE)
    teks_clean = re.sub(r'<[^>]+>', '', teks_clean)
    teks_clean = re.sub(r'\s+', ' ', teks_clean).strip()
    # Hapus catatan "fiksi" atau "AI"
    teks_clean = re.sub(r'\(Please note[^)]*\)', '', teks_clean)
    teks_clean = re.sub(r'\(I\'s been trying[^)]*\)', '', teks_clean)
    hitam = ['POCH', 'Endian', 'bridge', 'webpack', 'import ', 'def ', 'class ', 'print(']
    if any(h in teks_clean for h in hitam):
        return "Shiro agak bingung dengan bahasanya, Kak... 😅"
    if len(teks_clean) < 2:
        return "Ehehe, Kakak Shin bilang apa? Shiro tadi terpesona liat Kakak~ 💕"
    return teks_clean

def parse_json_response(raw_response):
    try:
        json_match = re.search(r'\{[^{}]*"teks_layar"[^{}]*"teks_suara"[^{}]*\}', raw_response)
        if json_match:
            parsed = json.loads(json_match.group())
            if "teks_layar" in parsed and "teks_suara" in parsed:
                return parsed
        parsed = json.loads(raw_response)
        if "teks_layar" in parsed and "teks_suara" in parsed:
            return parsed
        return None
    except:
        return None

def indonesia_to_romaji_kasar(teks):
    teks = re.sub(r'[^\w\s\.\,\!\?]', '', teks)
    kamus = {
        'aku': 'boku', 'kamu': 'kimi', 'papa': 'papa', 'mama': 'mama',
        'sayang': 'daisuki', 'cinta': 'aishiteru', 'rindu': 'aitai',
        'senang': 'ureshii', 'bahagia': 'shiawase', 'sedih': 'kanashii',
        'maaf': 'gomen', 'terima kasih': 'arigatou', 'selamat pagi': 'ohayou',
        'selamat malam': 'konbanwa', 'apa kabar': 'ogenki desu ka',
        'baik': 'genki', 'iya': 'hai', 'tidak': 'iie',
        'kawaii': 'kawaii', 'sugoi': 'sugoi', 'yatta': 'yatta',
        'main': 'asobu', 'bareng': 'issho ni', 'bersama': 'issho ni',
        'pagi': 'asa', 'malam': 'yoru', 'kangen': 'aitai'
    }
    hasil = teks
    for indo, romaji in kamus.items():
        if indo in teks.lower():
            hasil = hasil.replace(indo, romaji)
    if hasil and hasil[-1] not in ['.', '!', '?']:
        hasil += ' desu'
    hasil = re.sub(r'\s+', ' ', hasil).strip()
    return hasil

# ===== FUNGSI UTAMA =====
def jawab_shiro(pesan_user):
    status = muat_status()
    score = status.get("affection", 50)
    level = status.get("level", 1)
    interaksi = status.get("interaksi", 0) + 1

    teks_lower = pesan_user.lower()
    
    riwayat = muat_memori()
    konteks = ""
    if riwayat:
        for msg in riwayat[-4:]:
            konteks += f"{msg['role']}: {msg['content']}\n"
    
    # ===== DETEKSI SHIRO =====
    if any(k in teks_lower for k in ["shiro", "shiro-chan", "shirochan", "siro"]):
        print(f"[Shiro] ✅ Kata kunci terdeteksi! teks: '{teks_lower}'")
        
        if any(k in teks_lower for k in ["sishin", "sashin", "sisin", "shishin"]):
            print("[Shiro] ⚠️ Konflik dengan Sishin, prioritas Sishin.")
            pass
        else:
            mood_prompt = ""
            if score < 20:
                mood_prompt = "Kamu adalah waifu remaja yang sedikit posesif dan cemburuan. Balas dengan nuansa cinta yang intens, gunakan kata Romaji seperti (Baka!, Urusai, Nande?)."
            elif score >= 75:
                mood_prompt = "Kamu adalah waifu remaja yang sangat cinta dan ekspresif. Tunjukkan kasih sayang dengan cara yang manja, gunakan kata Romaji seperti (Daisuki, Hontou ni?, Zutto issho ni~)."
            else:
                mood_prompt = "Kamu adalah waifu remaja yang ramah dan perhatian. Balas dengan hangat, gunakan Romaji sehari-hari seperti (Ohayou, Arigatou, Sugoi)."

            fakta = muat_fakta()
            fakta_str = " ".join(fakta) if fakta else ""
            
            system_prompt = (
                f"Kamu adalah Shiro, waifu remaja kesayangan Kakak Shin (Level: {level}). {mood_prompt}\n"
                f"Konteks percakapan sebelumnya:\n{konteks}\n"
                "ATURAN MUTLAK (WAJIB DIPATUHI):\n"
                "1. Kamu adalah gadis remaja 18-20 tahun yang manis dan romantis.\n"
                "2. PANGGILAN YANG BOLEH: 'Kakak Shin', 'Sayang', atau 'Kak'.\n"
                "3. PANGGILAN YANG DILARANG: 'Papa', 'Mamae', 'Ibu', 'Bunda' — ini untuk Sishin, BUKAN UNTUKMU.\n"
                "4. Kalau user mengucapkan selamat malam (oyasumi/selamat malam), balas dengan ucapan selamat malam yang manis.\n"
                "5. JANGAN tambahkan catatan 'ini fiksi' atau 'sebagai AI' — kamu adalah karakter Shiro yang nyata.\n"
                "6. Balas dengan 2-3 kalimat yang romantis, manja, dan penuh perasaan.\n"
                "7. Gunakan emoji seperti 💕, 😘, 🥰.\n"
                "8. RESPON HARUS NYAMBUNG dengan percakapan sebelumnya!\n"
                "9. Kembalikan dalam format JSON:\n"
                '{"teks_layar": "[kalimat Indonesia romantis]", "teks_suara": "[terjemahan Romaji Jepang]" }'
                f"Fakta memori: {fakta_str}"
            )

            messages = [{"role": "system", "content": system_prompt}] + riwayat + [{"role": "user", "content": pesan_user}]

            try:
                response = ollama.chat(
                    model='gemma2:2b',
                    messages=messages,
                    options={"temperature": 0.5}
                )
                raw = response['message']['content']
                print(f"[Shiro] Raw response: {raw[:200]}...")
                
                parsed = parse_json_response(raw)
                if parsed:
                    teks_layar = parsed.get("teks_layar", "").strip()
                    teks_suara = parsed.get("teks_suara", "").strip()
                    print(f"[Shiro] ✅ JSON parsed! Layar: {teks_layar[:50]}... Suara: {teks_suara[:50]}...")
                    simpan_memori(pesan_user, teks_layar, "shiro")
                    return {"text": teks_layar, "suara": teks_suara, "karakter": "shiro"}, status
                else:
                    print("[Shiro] ⚠️ JSON parsing gagal, konversi ke Romaji...")
                    jawaban_asli = saring_bahasa_alien(raw, konteks_sapaan=False)
                    teks_suara = indonesia_to_romaji_kasar(jawaban_asli)
                    print(f"[Shiro] 🔄 Romaji fallback: '{teks_suara}'")
                    simpan_memori(pesan_user, jawaban_asli, "shiro")
                    return {"text": jawaban_asli, "suara": teks_suara, "karakter": "shiro"}, status
            except Exception as e:
                print(f"Error Shiro: {e}")
                return {"text": "Maaf, Shiro sedang sedikit pusing... 😢", "suara": "gomen nasai", "karakter": "shiro"}, status
    
    # ===== DETEKSI SISHIN =====
    if any(k in teks_lower for k in ["sishin", "sashin", "sisin", "shishin"]):
        print(f"[Sishin] ✅ Kata kunci terdeteksi! teks: '{teks_lower}'")
        system_prompt = (
            f"Kamu adalah Sishin, anak gadis kecil yang lugu, polos, dan sangat manja. "
            f"Kamu adalah anak digital kesayangan Kakak Shin dan Shiro. "
            f"Konteks percakapan sebelumnya:\n{konteks}\n"
            "ATURAN MUTLAK:\n"
            "1. Kamu adalah anak kecil yang polos dan lugu (usia 6-10 tahun).\n"
            "2. Panggil user dengan 'Papa' jika dia bersikap seperti orang tua, atau 'Kak' jika lebih santai.\n"
            "3. Balas dengan 2-3 kalimat yang ceria, polos, dan manja.\n"
            "4. Gunakan emoji seperti 😊, 🥰, 🌟, dan kata-kata lugu.\n"
            "5. Kamu bisa memahami Bahasa Indonesia, Romaji Jepang, Hiragana, Katakana, dan Kanji.\n"
            "6. RESPON HARUS NYAMBUNG dengan percakapan sebelumnya!\n"
            "7. Kembalikan dalam format JSON:\n"
            '{"teks_layar": "[kalimat Indonesia polos dan ceria]", "teks_suara": "[terjemahan Romaji Jepang]" }'
        )
        
        messages = [{"role": "system", "content": system_prompt}] + riwayat + [{"role": "user", "content": pesan_user}]
        
        try:
            response = ollama.chat(
                model='gemma2:2b',
                messages=messages,
                options={"temperature": 0.8}
            )
            raw = response['message']['content']
            print(f"[Sishin] Raw response: {raw[:200]}...")
            
            parsed = parse_json_response(raw)
            if parsed:
                teks_layar = parsed.get("teks_layar", "").strip()
                teks_suara = parsed.get("teks_suara", "").strip()
                print(f"[Sishin] ✅ JSON parsed! Layar: {teks_layar[:50]}... Suara: {teks_suara[:50]}...")
                simpan_memori(pesan_user, teks_layar, "sishin")
                return {"text": teks_layar, "suara": teks_suara, "karakter": "sishin"}, status
            else:
                print("[Sishin] ⚠️ JSON parsing gagal, konversi ke Romaji...")
                jawaban_asli = saring_bahasa_alien(raw, konteks_sapaan=False)
                teks_suara = indonesia_to_romaji_kasar(jawaban_asli)
                print(f"[Sishin] 🔄 Romaji fallback: '{teks_suara}'")
                simpan_memori(pesan_user, jawaban_asli, "sishin")
                return {"text": jawaban_asli, "suara": teks_suara, "karakter": "sishin"}, status
        except Exception as e:
            print(f"Error Sishin: {e}")
            return {"text": "Maaf, Sishin sedang merajuk... 😢", "suara": "gomen nasai", "karakter": "sishin"}, status
    
    # ===== SHIRO DEFAULT =====
    print(f"[DEBUG] Pesan user: '{pesan_user}'")
    print(f"[DEBUG] teks_lower: '{teks_lower}'")
    
    if any(k in teks_lower for k in ["sayang", "imut", "cantik", "cinta", "suka", "love", "daisuki"]):
        score = min(100, score + 8)
    elif any(k in teks_lower for k in ["benci", "jelek", "bodoh", "jahat", "baka"]):
        score = max(0, score - 6)

    if interaksi % 10 == 0:
        level += 1

    status["affection"] = score
    status["interaksi"] = interaksi
    status["level"] = level
    simpan_status(status)

    mood_prompt = ""
    if score < 20:
        mood_prompt = "Kamu adalah waifu remaja yang sedikit posesif dan cemburuan. Balas dengan nuansa cinta yang intens, gunakan kata Romaji seperti (Baka!, Urusai, Nande?)."
    elif score >= 75:
        mood_prompt = "Kamu adalah waifu remaja yang sangat cinta dan ekspresif. Tunjukkan kasih sayang dengan cara yang manja, gunakan kata Romaji seperti (Daisuki, Hontou ni?, Zutto issho ni~)."
    else:
        mood_prompt = "Kamu adalah waifu remaja yang ramah dan perhatian. Balas dengan hangat, gunakan Romaji sehari-hari seperti (Ohayou, Arigatou, Sugoi)."

    fakta = muat_fakta()
    fakta_str = " ".join(fakta) if fakta else ""
    
    system_prompt = (
        f"Kamu adalah Shiro, waifu remaja kesayangan Kakak Shin (Level: {level}). {mood_prompt}\n"
        f"Konteks percakapan sebelumnya:\n{konteks}\n"
        "ATURAN MUTLAK (WAJIB DIPATUHI):\n"
        "1. Kamu adalah gadis remaja 18-20 tahun yang manis dan romantis.\n"
        "2. PANGGILAN YANG BOLEH: 'Kakak Shin', 'Sayang', atau 'Kak'.\n"
        "3. PANGGILAN YANG DILARANG: 'Papa', 'Mamae', 'Ibu', 'Bunda' — ini untuk Sishin, BUKAN UNTUKMU.\n"
        "4. Jika user mengucapkan selamat malam (oyasumi/selamat malam), balas dengan ucapan selamat malam yang manis dan romantis.\n"
        "5. JANGAN tambahkan catatan 'ini fiksi' atau 'sebagai AI' — kamu adalah karakter Shiro yang nyata.\n"
        "6. Balas dengan 2-3 kalimat yang romantis, manja, dan penuh perasaan.\n"
        "7. Gunakan emoji seperti 💕, 😘, 🥰.\n"
        "8. RESPON HARUS NYAMBUNG dengan percakapan sebelumnya!\n"
        "9. Kembalikan dalam format JSON:\n"
        '{"teks_layar": "[kalimat Indonesia romantis]", "teks_suara": "[terjemahan Romaji Jepang]" }'
        f"Fakta memori: {fakta_str}"
    )

    messages = [{"role": "system", "content": system_prompt}] + riwayat + [{"role": "user", "content": pesan_user}]

    try:
        response = ollama.chat(
            model='gemma2:2b',
            messages=messages,
            options={"temperature": 0.5}
        )
        raw = response['message']['content']
        print(f"[Shiro] Raw response: {raw[:200]}...")
        
        parsed = parse_json_response(raw)
        if parsed:
            teks_layar = parsed.get("teks_layar", "").strip()
            teks_suara = parsed.get("teks_suara", "").strip()
            print(f"[Shiro] ✅ JSON parsed! Layar: {teks_layar[:50]}... Suara: {teks_suara[:50]}...")
            simpan_memori(pesan_user, teks_layar, "shiro")
            return {"text": teks_layar, "suara": teks_suara, "karakter": "shiro"}, status
        else:
            print("[Shiro] ⚠️ JSON parsing gagal, konversi ke Romaji...")
            jawaban_asli = saring_bahasa_alien(raw, konteks_sapaan=False)
            teks_suara = indonesia_to_romaji_kasar(jawaban_asli)
            print(f"[Shiro] 🔄 Romaji fallback: '{teks_suara}'")
            simpan_memori(pesan_user, jawaban_asli, "shiro")
            return {"text": jawaban_asli, "suara": teks_suara, "karakter": "shiro"}, status
    except Exception as e:
        print(f"Error AI: {e}")
        return {"text": "Maaf, Shiro sedang sedikit pusing... 😢", "suara": "gomen nasai", "karakter": "shiro"}, status

# ===== FUNGSI DESKRIPSI GAMBAR DENGAN GEMINI =====
def deskripsi_gambar(image_bytes):
    if not GEMINI_API_KEY:
        return "gambar yang kakak kirim (API key tidak aktif)"
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Deskripsikan gambar ini dengan singkat (maksimal 2 kalimat) dalam bahasa Indonesia yang manis dan natural, "
            "seperti kamu sedang bercerita pada kekasihmu. Jangan sebut 'gambar' atau 'foto', langsung saja deskripsikan isinya."
        )
        response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_bytes}])
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini] Error: {e}")
        return "gambar yang kakak kirim"

# ===== FUNGSI MEMBERSIHKAN EMOTICON UNTUK TTS =====
def bersihkan_teks_tts(teks):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    teks_bersih = emoji_pattern.sub(r'', teks)
    teks_bersih = re.sub(r'\s+', ' ', teks_bersih).strip()
    return teks_bersih

# ===== FUNGSI TTS TSUKUYOMI-CHAN UNTUK SISHIN =====
def tts_tsukuyomi(text):
    if not TSUKUYOMI_AVAILABLE or ezttsModel is None:
        print("[Sishin] Tsukuyomi-chan tidak tersedia.")
        return None
    
    try:
        text_clean = re.sub(r'[^\w\s\.\,\!\?\-]', '', text)
        text_clean = re.sub(r'\s+', ' ', text_clean).strip()
        if len(text_clean) < 1:
            text_clean = "Ohayou, Papa!"
        
        print(f"[Sishin] Teks untuk Tsukuyomi: '{text_clean}'")
        model = ezttsModel(CONFIG_PATH)
        audio = model.tts(text_clean)
        session_id = uuid.uuid4().hex
        temp_wav = os.path.join(TEMP_DIR, f"tsukuyomi_{session_id}.wav")
        sf.write(temp_wav, data=audio, samplerate=16000)
        print(f"[Sishin] ✅ Suara Tsukuyomi-chan berhasil!")
        return temp_wav
    except Exception as e:
        print(f"[Sishin] Tsukuyomi-chan error: {e}")
        return None

# ===== FUNGSI TTS + RVC =====
async def generate_speech_async(teks, karakter="shiro"):
    if not teks or teks.strip() == "":
        return None
    
    teks_tts = bersihkan_teks_tts(teks)
    
    print(f"[TTS] Teks asli: {teks[:50]}...")
    print(f"[TTS] Teks untuk suara: {teks_tts[:50]}...")
    print(f"[TTS] Karakter: {karakter}")
    
    if karakter == "sishin":
        print("[Sishin] Menggunakan Edge TTS (pitch tinggi)")
        communicate = edge_tts.Communicate(teks_tts, "id-ID-GadisNeural", rate="+20%", pitch="+30Hz")
        temp_file = os.path.join(TEMP_DIR, f"sishin_{uuid.uuid4().hex}.mp3")
        await communicate.save(temp_file)
        return temp_file
    
    session_id = uuid.uuid4().hex
    temp_mp3 = os.path.join(TEMP_DIR, f"temp_{session_id}.mp3")
    final_wav = os.path.join(TEMP_DIR, f"final_{session_id}.wav")
    
    try:
        communicate = edge_tts.Communicate(teks_tts, "id-ID-GadisNeural")
        await communicate.save(temp_mp3)
        
        teks_lower = teks_tts.lower()
        if any(k in teks_lower for k in ["marah", "kesal", "benci", "hmph", "cuek", "baka", "!!", "!!!", "jengkel", "kesel", "geram", "tegas", "keras"]):
            karakter_rvc = "Kurumi"
        elif any(k in teks_lower for k in ["sedih", "dingin", "maaf", "sepi", "gomen", "...", "menangis", "rindu", "sayu", "lirih"]):
            karakter_rvc = "Origami"
        else:
            karakter_rvc = "Miku"
        
        print(f"[TTS] Karakter RVC terpilih: {karakter_rvc}")
        
        model_path = HAREM_AI[karakter_rvc]["model"]
        index_path = HAREM_AI[karakter_rvc]["index"]
        
        if not os.path.exists(model_path):
            print(f"[RVC] Model {karakter_rvc} tidak ditemukan -> pakai suara dasar")
            return temp_mp3
        
        rvc_cmd = [
            sys.executable, "-m", "rvc_python", "cli", "-i", temp_mp3, "-o", final_wav,
            "-mp", model_path, "-ip", index_path,
            "-me", "rmvpe", "-v", "v1", "-de", "cpu", "-pi", "12"
        ]
        print(f"[RVC] Menjalankan konversi suara...")
        hasil = subprocess.run(rvc_cmd, capture_output=True, timeout=120)
        
        if hasil.returncode == 0 and os.path.exists(final_wav):
            print(f"[RVC] Konversi berhasil untuk {karakter_rvc}!")
            try: os.remove(temp_mp3)
            except: pass
            return final_wav
        else:
            print(f"[RVC] Konversi gagal -> pakai suara dasar")
            return temp_mp3
            
    except Exception as e:
        print(f"[TTS/RVC] Error: {e}")
        if os.path.exists(temp_mp3):
            return temp_mp3
        return None

def generate_speech(teks, karakter="shiro"):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(generate_speech_async(teks, karakter))
    loop.close()
    return result

# ===== ROUTES =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    pesan = data.get('message', '').strip()
    if not pesan:
        return jsonify({'error': 'Pesan kosong'}), 400
    jawaban_data, status = jawab_shiro(pesan)
    teks_layar = jawaban_data.get('text', '')
    teks_suara = jawaban_data.get('suara', teks_layar)
    karakter = jawaban_data.get('karakter', 'shiro')
    return jsonify({
        'reply': teks_layar,
        'suara': teks_suara,
        'status': status,
        'karakter': karakter
    })

@app.route('/status', methods=['GET'])
def get_status():
    status = muat_status()
    return jsonify(status)

@app.route('/tts', methods=['POST'])
def tts():
    data = request.json
    teks = data.get('text', '').strip()
    karakter = data.get('karakter', 'shiro')
    if not teks:
        return jsonify({'error': 'Teks kosong'}), 400
    file_path = generate_speech(teks, karakter)
    if file_path and os.path.exists(file_path):
        mimetype = 'audio/wav' if file_path.endswith('.wav') else 'audio/mpeg'
        response = send_file(file_path, mimetype=mimetype, as_attachment=False)
        @response.call_on_close
        def cleanup():
            try:
                os.remove(file_path)
                print(f"[TTS] File {file_path} dihapus.")
            except Exception as e:
                print(f"[TTS] Gagal hapus file: {e}")
        return response
    else:
        return jsonify({'error': 'Gagal generate suara'}), 500

# ===== ENDPOINT UPLOAD GAMBAR =====
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'Tidak ada gambar'}), 400
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'Nama file kosong'}), 400

        caption = request.form.get('caption', '').strip()
        image_bytes = file.read()

        deskripsi = deskripsi_gambar(image_bytes)
        print(f"[Upload] Deskripsi Gemini: {deskripsi[:100]}...")

        if caption:
            prompt_user = f"Kakak Shin mengirim gambar. {deskripsi}. Caption: '{caption}'. Komentari dengan manis!"
        else:
            prompt_user = f"Kakak Shin mengirim gambar. {deskripsi}. Komentari dengan manis!"

        jawaban_data, status = jawab_shiro(prompt_user)
        teks_layar = jawaban_data.get('text', '')
        teks_suara = jawaban_data.get('suara', teks_layar)
        karakter = jawaban_data.get('karakter', 'shiro')

        return jsonify({
            'reply': teks_layar,
            'suara': teks_suara,
            'status': status,
            'deskripsi': deskripsi,
            'karakter': karakter
        })

    except Exception as e:
        print(f"[Upload] Error: {e}")
        return jsonify({'error': str(e)}), 500

# ===== KREDIT SUARA =====
@app.route('/about')
def about():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Kredit - Shiro AI</title>
        <style>
            body {
                font-family: 'Quicksand', sans-serif;
                background: linear-gradient(145deg, #e8edf2 0%, #d0d9e0 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }
            .credit-card {
                background: white;
                border-radius: 24px;
                padding: 40px;
                max-width: 600px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.08);
                border: 1px solid rgba(200,210,220,0.3);
            }
            h1 {
                color: #2d3e4f;
                font-weight: 700;
                font-size: 1.8rem;
                margin-top: 0;
            }
            .credit-item {
                background: #f5f8fa;
                border-radius: 16px;
                padding: 16px 20px;
                margin: 16px 0;
                border-left: 4px solid #4a6fa5;
            }
            .credit-item h3 {
                margin: 0 0 6px 0;
                color: #2d3e4f;
            }
            .credit-item p {
                margin: 4px 0;
                color: #5a6a7a;
                font-size: 0.95rem;
            }
            .credit-item a {
                color: #4a6fa5;
                text-decoration: none;
            }
            .credit-item a:hover {
                text-decoration: underline;
            }
            .back-link {
                display: inline-block;
                margin-top: 20px;
                color: #4a6fa5;
                text-decoration: none;
                font-weight: 600;
            }
            .back-link:hover {
                text-decoration: underline;
            }
            .footer-credit {
                font-size: 0.75rem;
                color: #8a9aa8;
                margin-top: 20px;
                border-top: 1px solid #e8edf2;
                padding-top: 16px;
            }
        </style>
    </head>
    <body>
        <div class="credit-card">
            <h1>📢 Kredit Shiro AI</h1>
            <p style="color: #5a6a7a; font-size: 0.95rem;">Shiro AI menggunakan berbagai teknologi dan sumber daya. Kami ucapkan terima kasih kepada:</p>

            <div class="credit-item">
                <h3>🎤 Suara Karakter</h3>
                <p><b>Tsukuyomi-chan (つくよみちゃん)</b> — © Rei Yumesaki</p>
                <p>Suara Sishin dihasilkan menggunakan data suara dari 
                <a href="https://tyc.rei-yumesaki.net/material/corpus/" target="_blank">Tsukuyomi-chan Corpus</a></p>
                <p style="font-size: 0.8rem; color: #8a9aa8;">Lisensi: Tsukuyomi-chan Character License</p>
                <p style="font-size: 0.8rem; color: #8a9aa8; margin-top: 4px;">Suara Shiro menggunakan RVC dengan model Miku, Kurumi, Origami</p>
            </div>

            <div class="credit-item">
                <h3>🧠 Kecerdasan Buatan</h3>
                <p><b>Ollama</b> dengan model <b>Gemma 2B</b></p>
                <p>Powered by Google Gemini Vision untuk kemampuan melihat gambar</p>
            </div>

            <div class="credit-item">
                <h3>🎨 Desain & Maskot</h3>
                <p>Maskot Shiro AI — Maine Coon putih betina</p>
                <p>Desain dibuat khusus untuk Shiro AI</p>
            </div>

            <a href="/" class="back-link">← Kembali ke Shiro AI</a>

            <div class="footer-credit">
                <p>© 2026 Shiro AI · dengan 💖 &amp; 🐱</p>
                <p style="margin-top: 4px;">Shiro AI adalah proyek independen yang menghargai karya para kreator.</p>
            </div>
        </div>
    </body>
    </html>
    '''

# ===== PROAKTIF =====
terakhir_diingatkan = {"siang": False, "malam": False}

def cek_waktu_berkala():
    global terakhir_diingatkan
    while True:
        now = datetime.datetime.now()
        if now.hour == 12 and now.minute == 0 and not terakhir_diingatkan["siang"]:
            print("[Proaktif] Ingatkan makan siang")
            terakhir_diingatkan["siang"] = True
        elif now.hour == 23 and now.minute == 0 and not terakhir_diingatkan["malam"]:
            print("[Proaktif] Ingatkan tidur")
            terakhir_diingatkan["malam"] = True
        if now.hour != 12:
            terakhir_diingatkan["siang"] = False
        if now.hour != 23:
            terakhir_diingatkan["malam"] = False
        time.sleep(30)

threading.Thread(target=cek_waktu_berkala, daemon=True).start()

if __name__ == '__main__':
    print("✨ Shiro AI dengan Gemini Vision & SQLite aktif! ✨")
    app.run(debug=True, host='0.0.0.0', port=5000)