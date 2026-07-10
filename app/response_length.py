"""Panjang respons adaptif Shiro & Sishin — pendek, sedang, atau panjang sesuai konteks."""
from __future__ import annotations

import re

MODES = ("short", "medium", "long")

MODE_CONFIG = {
    "short": {
        "max_tokens": 100,
        "max_chars": 220,
        "sentences": "1–3 kalimat",
        "ollama_predict": 120,
    },
    "medium": {
        "max_tokens": 280,
        "max_chars": 550,
        "sentences": "3–6 kalimat",
        "ollama_predict": 260,
    },
    "long": {
        "max_tokens": 560,
        "max_chars": 1100,
        "sentences": "6–12 kalimat",
        "ollama_predict": 480,
    },
}

SHORT_HINTS = (
    "singkat", "pendek", "cepat", "ringkas", "ga usah panjang", "gak usah panjang",
    "jangan panjang", "singkat aja", "pendek aja", "ok?", "iya", "tidak", "gak",
    "thanks", "makasih", "thx", "halo", "hai", "hi", "pagi", "malam", "bye",
    "dadah", "yoi", "sip", "oke", "ok",
)

LONG_HINTS = (
    "ceritain", "cerita", "curhat", "detail", "jelasin", "jelaskan", "panjang",
    "banyak", "lanjut", "terus", "momen", "ngobrol", "obrol", "gimana menurut",
    "menurutmu", "pendapat", "alasan", "kenapa", "mengapa", "gimana caranya",
    "step by step", "semua", "lengkap", "deep talk", "bosan", "kesepian",
    "galau", "stress", "sedih", "khawatir", "takut", "bingung banget",
    "mau cerita", "dengerin", "temani", "temani aku", "ngobrol yuk",
    "apa yang kamu pikir", "apa yang kamu rasakan", "sharing", "sharing session",
)

OPEN_QUESTION_STARTS = (
    "gimana", "bagaimana", "kenapa", "mengapa", "apa yang", "apakah menurut",
    "ceritain", "cerita", "jelasin", "jelaskan", "bisa ga", "bisa gak",
    "momen", "pengalaman", "perasaan",
)


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def decide_response_length(
    pesan_user: str,
    konteks: str = "",
    karakter: str = "shiro",
    affection: int = 50,
) -> tuple[str, dict]:
    """
    Tentukan mode respons: short | medium | long.
    Default medium — tidak selalu pendek atau panjang.
    """
    text = (pesan_user or "").strip()
    lower = text.lower()
    words = _word_count(text)
    ctx_len = len(konteks or "")

    if any(h in lower for h in SHORT_HINTS) and not any(h in lower for h in LONG_HINTS):
        mode = "short"
    elif any(h in lower for h in LONG_HINTS):
        mode = "long"
    elif words >= 35 or len(text) >= 180:
        mode = "long"
    elif words >= 12 or len(text) >= 55:
        mode = "medium"
    elif any(lower.startswith(q) or f" {q}" in lower for q in OPEN_QUESTION_STARTS):
        mode = "medium" if words < 8 else "long"
    elif words <= 4 and len(text) < 28:
        mode = "short"
    elif ctx_len > 400 and words >= 6:
        # Obrolan sudah mengalir — lanjutkan dengan respons lebih substantif
        mode = "medium"
    else:
        mode = "medium"

    # Shiro lebih ekspresif saat afeksi tinggi; Sishin lebih ramai saat excited
    if mode == "medium" and affection >= 72 and karakter == "shiro":
        if any(w in lower for w in ("sayang", "kangen", "rindu", "cinta", "love")):
            mode = "long"
    if mode == "medium" and karakter == "sishin":
        if any(w in lower for w in ("seru", "asik", "main", "yuk", "hore")):
            mode = "long"

    meta = dict(MODE_CONFIG[mode])
    meta["mode"] = mode
    return mode, meta


def format_length_instruction(mode: str, karakter: str) -> str:
    cfg = MODE_CONFIG.get(mode, MODE_CONFIG["medium"])
    sentences = cfg["sentences"]

    if mode == "short":
        tone = (
            "Respons RINGKAS — {sentences}, to the point, tetap hangat."
        )
    elif mode == "long":
        tone = (
            "Respons PANJANG & KAYA — {sentences}. Boleh cerita, elaborasi perasaan, "
            "contoh kecil, reaksi berlapis, atau momen imut. Jangan terpotong di tengah. "
            "Buat obrolan terasa hidup seperti teman curhat, bukan cuma balasan singkat."
        )
    else:
        tone = (
            "Respons SEDANG — {sentences}, natural dan nyambung. Cukup detail tanpa "
            "terlalu pendek atau terlalu panjang."
        )

    voice_note = (
        "teks_layar boleh lebih panjang; teks_suara versi natural untuk TTS "
        "(boleh sedikit lebih ringkas tapi JANGAN cuma 1 kalimat kering)."
    )
    if mode == "long":
        voice_note = (
            "teks_layar panjang penuh; teks_suara tetap lengkap dan enak didengar "
            "(boleh 4–8 kalimat, jangan dipotong jadi sapaan pendek saja)."
        )

    char_flavor = ""
    if karakter == "shiro" and mode == "long":
        char_flavor = "Shiro: manja, perhatian, bisa curhat balik atau cerita momen manis."
    elif karakter == "sishin" and mode == "long":
        char_flavor = "Sishin: ceria, antusias, banyak reaksi imut dan tanya balik."

    block = (
        f"PANJANG RESPONS (mode={mode}):\n"
        f"- {tone.format(sentences=sentences)}\n"
        f"- {voice_note}\n"
    )
    if char_flavor:
        block += f"- {char_flavor}\n"
    return block
