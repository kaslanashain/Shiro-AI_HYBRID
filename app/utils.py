import hashlib
import json
import logging
import re
from collections import OrderedDict

from app.config import MAX_CACHE

logger = logging.getLogger(__name__)

respon_cache = OrderedDict()


def get_cache_key(pesan, konteks, karakter):
    return hashlib.md5(f"{karakter}_{pesan}_{konteks[-200:]}".encode()).hexdigest()


def cache_get(key):
    if key not in respon_cache:
        return None
    respon_cache.move_to_end(key)
    return respon_cache[key]


def cache_set(key, value):
    respon_cache[key] = value
    respon_cache.move_to_end(key)
    while len(respon_cache) > MAX_CACHE:
        respon_cache.popitem(last=False)


def detect_input_language(text):
    for char in text:
        code = ord(char)
        if 0x3040 <= code <= 0x30FF or 0x4E00 <= code <= 0x9FFF:
            return "ja"
    return "id"


def validasi_respon_teks(teks, konteks):
    if not teks:
        return False
    for angka in re.findall(r"\b\d{1,4}\b", teks):
        if angka not in konteks and len(angka) > 2:
            return False
    pola_fakta = ["tahun", "tanggal", "berat", "tinggi", "umur", "jarak", "kecepatan"]
    teks_lower = teks.lower()
    konteks_lower = konteks.lower()
    if any(p in teks_lower for p in pola_fakta):
        if not any(p in konteks_lower for p in pola_fakta):
            return False
    if len(teks) > 300:
        return False
    return True


def sync_text_and_voice(teks_layar, teks_suara):
    layar = (teks_layar or "").strip()
    suara = (teks_suara or layar).strip() or layar
    suara_bersih = bersihkan_teks_tts(suara)
    return layar, suara_bersih or layar


def saring_bahasa_alien(teks):
    teks_clean = str(teks).strip()
    teks_clean = teks_clean.replace("*", "").replace("_", "").replace('"', "").replace("`", "")
    teks_clean = re.sub(r"^shiro:\s*", "", teks_clean, flags=re.IGNORECASE)
    teks_clean = re.sub(r"<[^>]+>", "", teks_clean)
    teks_clean = re.sub(r"\s+", " ", teks_clean).strip()
    teks_clean = re.sub(r"\(Please note[^)]*\)", "", teks_clean)
    teks_clean = re.sub(r"\(I\'s been trying[^)]*\)", "", teks_clean)
    hitam = ["POCH", "Endian", "bridge", "webpack", "import ", "def ", "class ", "print("]
    if any(h in teks_clean for h in hitam):
        return "Shiro agak bingung dengan bahasanya, Kak"
    if len(teks_clean) < 2:
        return "Ehehe, Kakak Shin bilang apa? Shiro tadi terpesona liat Kakak"
    return teks_clean


def parse_json_response(raw_response):
    if not raw_response:
        return None
    try:
        start = raw_response.find("{")
        end = raw_response.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(raw_response[start : end + 1])
            if "teks_layar" in parsed and "teks_suara" in parsed:
                return parsed
    except json.JSONDecodeError:
        logger.debug("JSON parse failed for model response")
    return None


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
        flags=re.UNICODE,
    )
    teks_bersih = emoji_pattern.sub("", teks)
    return re.sub(r"\s+", " ", teks_bersih).strip()


def build_konteks(riwayat, limit=4):
    if not riwayat:
        return ""
    return "".join(f"{msg['role']}: {msg['content']}\n" for msg in riwayat[-limit:])
