"""Soft-filtered learning from user interactions for Shiro & Sishin."""
import hashlib
import logging
import re
import threading
from typing import Optional

from app.db import muat_pembelajaran, simpan_pembelajaran

logger = logging.getLogger(__name__)

# Lembut: cukup rendah agar interaksi ringan tetap bisa belajar jika ada isi berguna
MIN_VALUE_SCORE = 0.28
MAX_LEARNINGS_PROMPT = 10

# Respons sistem / fallback — jangan disimpan
_SKIP_ASSISTANT_MARKERS = (
    "sedang sedikit pusing",
    "lagi capek",
    "agak bingung",
    "coba bilang lagi",
    "bisa diulang",
)

# Ack singkat — kurangi skor, bukan blok total
_LOW_VALUE_ACKS = frozenset({
    "ok", "oke", "ya", "iya", "yoi", "hmm", "hm", "ah", "oh", "ui", "yup", "no",
    "nope", "thanks", "thank you", "thx", "makasih", "mksh", "sip", "siap",
})

_GREETING_ONLY = frozenset({
    "halo", "hai", "hello", "hi", "hey", "pagi", "siang", "sore", "malam",
    "selamat pagi", "selamat siang", "selamat malam", "yo", "test",
})

_LAUGHTER = re.compile(r"^(?:wkwk+|kwkw+|haha+|hehe+|lol+|w(?!a)[a-z]*)$", re.I)

_PERSONAL_PATTERNS = [
    (re.compile(r"(?:nama (?:aku|saya|gue|gw)|panggil (?:aku|saya)) (?:adalah|itu|nya)?\s*(.+)", re.I), "fact", 0.85),
    (re.compile(r"(?:aku|saya|gue) (?:suka|senang|suka banget|doakan|fan(?:nya)?|cinta) (.+)", re.I), "preference", 0.8),
    (re.compile(r"(?:aku|saya) (?:tidak suka|benci|anti|ga suka|gak suka) (.+)", re.I), "preference", 0.75),
    (re.compile(r"(?:hobi|hobiku|kesukaanku) (?:aku|saya)?(?: adalah| itu|:)?\s*(.+)", re.I), "preference", 0.8),
    (re.compile(r"(?:ulang tahun|birthday|ultah)(?:ku| saya)?(?: tanggal| pada| di)?\s*(.+)", re.I), "fact", 0.9),
    (re.compile(r"(?:besok|lusa|nanti|hari ini|minggu ini) (?:aku|saya|gue) (.+)", re.I), "fact", 0.7),
    (re.compile(r"(?:kerja|kuliah|sekolah|ngampus)(?:ku| saya)?(?: di| sebagai| sebagai)?\s*(.+)", re.I), "fact", 0.75),
    (re.compile(r"(?:tinggal|domisili|rumah)(?:ku| saya)?(?: di| di)?\s*(.+)", re.I), "fact", 0.75),
]

_EMOTION_PATTERNS = [
    (re.compile(r"(?:aku|saya) (?:lagi|sedang) (?:senang|bahagia|sedih|kecewa|marah|stress|stres|capek|lelah|khawatir|takut|excited|semangat)(?: banget| sekali)?", re.I), "emotion", 0.65),
    (re.compile(r"(?:hari ini|kemarin|minggu ini) (?:aku|saya) (.+(?:senang|sedih|marah|stress|capek|lelah).*)", re.I), "emotion", 0.6),
]

_HABIT_PATTERNS = [
    (re.compile(r"(?:biasanya|sering|kadang) (?:aku|saya|gue) (.+)", re.I), "habit", 0.7),
    (re.compile(r"(?:setiap|tiap) (?:hari|pagi|malam|weekend) (?:aku|saya|gue)?\s*(.+)", re.I), "habit", 0.65),
]

_TOPIC_PATTERNS = [
    (re.compile(r"(?:ceritain|cerita|ngomongin|bahas|topik) (.+)", re.I), "topic", 0.55),
    (re.compile(r"(?:tanya|tanyain) (?:tentang|soal) (.+)", re.I), "topic", 0.5),
]

_VOICE_CMD = re.compile(
    r"\b(?:buka|jalankan|launch|open|start|run|matikan|tutup)\b",
    re.I,
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _content_hash(content: str) -> str:
    return hashlib.md5(_normalize(content).encode("utf-8")).hexdigest()


def score_interaction_value(
    user_msg: str,
    assistant_msg: str = "",
    *,
    is_fallback: bool = False,
    is_voice_command: bool = False,
) -> float:
    """Skor 0–1: filter lembut — rendah = kurang berguna, bukan dilarang."""
    user = (user_msg or "").strip()
    assistant = (assistant_msg or "").strip()

    if not user or is_fallback:
        return 0.0

    if is_voice_command or _VOICE_CMD.search(user):
        return 0.15

    if user in ("[foto]", "[video]") or user.startswith("[") and user.endswith("]"):
        return 0.1

    lower = user.lower()
    score = 0.45

    if any(m in assistant.lower() for m in _SKIP_ASSISTANT_MARKERS):
        return 0.12

    # Panjang & substansi
    if len(user) >= 80:
        score += 0.2
    elif len(user) >= 35:
        score += 0.12
    elif len(user) >= 12:
        score += 0.05
    elif len(user) < 4:
        score -= 0.25

    # Ack / greeting saja
    compact = re.sub(r"[^\w\s]", "", lower).strip()
    if compact in _LOW_VALUE_ACKS:
        score -= 0.3
    if compact in _GREETING_ONLY:
        score -= 0.2
    if _LAUGHTER.match(compact):
        score -= 0.25

    # Isi berguna
    if any(k in lower for k in ("ingat ya", "jangan lupa", "remember", "catat")):
        score += 0.35
    if any(k in lower for k in ("suka", "benci", "hobi", "nama", "ultah", "birthday", "kerja", "kuliah")):
        score += 0.15
    if "?" in user and len(user) > 15:
        score += 0.08
    if re.search(r"\b(?:aku|saya|gue|gw)\b", lower):
        score += 0.1

    return max(0.0, min(1.0, score))


def _clean_capture(text: str, max_len: int = 120) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    text = text.rstrip(".,!?~")
    if len(text) > max_len:
        text = text[: max_len - 1].rsplit(" ", 1)[0] + "…"
    return text


def extract_learnings(user_msg: str, karakter: str) -> list[dict]:
    """Ekstraksi rule-based — tanpa LLM tambahan di hot path."""
    user = (user_msg or "").strip()
    if not user:
        return []

    learnings = []
    seen_hashes = set()

    def _add(content: str, category: str, confidence: float, scope: str = "both"):
        content = _clean_capture(content)
        if len(content) < 3:
            return
        h = _content_hash(content)
        if h in seen_hashes:
            return
        seen_hashes.add(h)
        learnings.append({
            "content": content,
            "category": category,
            "confidence": confidence,
            "karakter": scope,
            "source_hash": h,
        })

    for pattern, category, conf in _PERSONAL_PATTERNS:
        m = pattern.search(user)
        if m:
            _add(m.group(1) if m.lastindex else user, category, conf)

    for pattern, category, conf in _EMOTION_PATTERNS:
        m = pattern.search(user)
        if m:
            _add(m.group(0) if m.lastindex is None else m.group(1), category, conf)

    for pattern, category, conf in _HABIT_PATTERNS:
        m = pattern.search(user)
        if m:
            _add(m.group(1) if m.lastindex else user, category, conf)

    for pattern, category, conf in _TOPIC_PATTERNS:
        m = pattern.search(user)
        if m:
            _add(m.group(1), category, conf)

    # Fallback lembut: kalimat panjang tentang diri user tanpa pola spesifik
    if len(user) >= 25 and re.search(r"\b(?:aku|saya|gue|gw)\b", user, re.I):
        if not learnings and not user.endswith("?"):
            _add(user, "context", 0.45, scope=karakter)

    return learnings


def _should_skip_assistant(assistant_msg: str, profile: Optional[dict]) -> bool:
    if not assistant_msg or not profile:
        return False
    lower = assistant_msg.lower()
    if any(m in lower for m in _SKIP_ASSISTANT_MARKERS):
        return True
    if assistant_msg.strip() == profile.get("fallback", "").strip():
        return True
    return False


def maybe_learn_from_turn(
    user_msg: str,
    assistant_msg: str,
    karakter: str,
    user_id=None,
    *,
    is_fallback: bool = False,
    is_voice_command: bool = False,
    profile: Optional[dict] = None,
):
    """Simpan pembelajaran berguna; dipanggil setelah balasan sukses."""
    if _should_skip_assistant(assistant_msg, profile):
        return

    value_score = score_interaction_value(
        user_msg,
        assistant_msg,
        is_fallback=is_fallback,
        is_voice_command=is_voice_command,
    )
    if value_score < MIN_VALUE_SCORE:
        logger.debug("Learning skipped (score=%.2f): %s", value_score, user_msg[:40])
        return

    items = extract_learnings(user_msg, karakter)
    if not items and value_score >= 0.55 and len((user_msg or "").strip()) >= 20:
        # Interaksi bermakna tanpa pola — simpan ringkas sebagai konteks
        items = [{
            "content": _clean_capture(user_msg),
            "category": "context",
            "confidence": min(0.55, value_score),
            "karakter": karakter,
            "source_hash": _content_hash(user_msg),
        }]

    for item in items:
        item_value = value_score * item["confidence"]
        if item_value < MIN_VALUE_SCORE * 0.85:
            continue
        simpan_pembelajaran(
            user_id=user_id,
            content=item["content"],
            category=item["category"],
            karakter=item["karakter"],
            source_hash=item["source_hash"],
            confidence=item["confidence"],
            value_score=item_value,
        )


def schedule_learning(
    user_msg: str,
    assistant_msg: str,
    karakter: str,
    user_id=None,
    **kwargs,
):
    """Jalankan pembelajaran di background agar tidak lambatkan chat."""
    def _run():
        try:
            maybe_learn_from_turn(
                user_msg, assistant_msg, karakter, user_id, **kwargs
            )
        except Exception:
            logger.exception("Background learning failed")

    threading.Thread(target=_run, daemon=True).start()


def format_learnings_block(karakter: str, user_id=None) -> str:
    """Format pembelajaran untuk system prompt."""
    rows = muat_pembelajaran(
        user_id=user_id,
        karakter=karakter,
        limit=MAX_LEARNINGS_PROMPT,
        min_confidence=0.4,
    )
    if not rows:
        return ""

    lines = []
    for row in rows:
        cat = row.get("category", "info")
        lines.append(f"- [{cat}] {row['content']}")

    return (
        "HAL YANG KAMU PELAJARI DARI INTERAKSI SEBELUMNYA (gunakan natural, jangan sebut 'database'):\n"
        + "\n".join(lines)
        + "\n"
    )
