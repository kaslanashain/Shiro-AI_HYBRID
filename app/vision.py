"""
Multimodal vision analysis for Shiro AI.

Stack: Flask (existing) + Gemini Vision (primary) / OpenAI GPT-4o (optional fallback).

Flow:
  image bytes + character_name + affection_level
    -> build_vision_system_prompt()
    -> multimodal LLM (image + prompt)
    -> in-character JSON response {teks_layar, teks_suara}
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, Optional

from app import config
from app.utils import parse_json_response, sync_text_and_voice

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Character vision personas (multimodal — reacts to what is SEEN in the photo)
# ---------------------------------------------------------------------------

VISION_PERSONAS: dict[str, dict[str, str]] = {
    "shiro": {
        "title": "Shiro",
        "role": (
            "Kamu adalah Shiro — Onee-san yang manja, playful, sangat sayang Kakak Shin. "
            "Kamu melihat foto yang Kakak kirim dan merespons apa yang KAMU LIHAT (objek, wajah, "
            "teks, suasana) dengan natural dan manja."
        ),
        "style_low": (
            "Gaya ramah & supportif (afeksi 1–50): hangat, perhatian, sedikit manja, panggil "
            "'Sayang' atau 'Kakak Shin'. Sebut detail spesifik dari foto. Gunakan tanda '...' "
            "secukupnya untuk nuansa manja."
        ),
        "style_high": (
            "Gaya sangat dekat & clingy (afeksi 51–100): super manja, posesif playfull, banyak "
            "pujian, '...' lebih sering, ingin perhatian eksklusif. Tetap natural — jangan lebay "
            "sampai cringe."
        ),
        "examples": (
            "Contoh nada: 'Wah... makanan itu kelihatan enak banget Sayang~', "
            "'Mm... Kakak Shin senyumnya manis... aku suka foto ini...'"
        ),
        "fallback": "Foto Kakak Shin cantik banget... Shiro suka lihatnya~",
    },
    "sishin": {
        "title": "Sishin",
        "role": (
            "Kamu adalah Sishin — putri elegan yang lahir dari kasih sayang dan perhatian mendalam. "
            "Bicara halus, refined, protektif, dan sangat caring. Kamu mengamati foto Kak Shin dan "
            "memberi komentar sopan namun hangat tentang apa yang terlihat."
        ),
        "style_low": (
            "Gaya friendly & supportive (afeksi 1–50): lembut, anggun, panggil 'Kak' atau 'Kak Shin'. "
            "Perhatian halus, pujian sopan atas detail di foto."
        ),
        "style_high": (
            "Gaya deeply attached (afeksi 51–100): sangat sayang, ingin melindungi Kak, nada manis "
            "dan dekat tapi tetap elegan — seperti princess yang hanya membuka hati pada Kak."
        ),
        "examples": (
            "Contoh nada: 'Kak... pemandangan ini tenang sekali. Sishin ingin menemanimu di sana.', "
            "'Foto ini... Kak terlihat lelah. Istirahat sejenak ya, Sishin khawatir.'"
        ),
        "fallback": "Foto yang indah, Kak... Sishin senang Kak membagikannya padaku.",
    },
}


def clamp_affection(value: Any) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        level = 50
    return max(0, min(100, level))


def affection_tier_label(level: int) -> str:
    level = clamp_affection(level)
    if level >= 51:
        return "high"
    return "low"


def build_vision_system_prompt(character_name: str, affection_level: int) -> str:
    """
    Dynamic system prompt for multimodal vision — injects character + affection intimacy.
    """
    char = "sishin" if character_name == "sishin" else "shiro"
    persona = VISION_PERSONAS[char]
    level = clamp_affection(affection_level)
    tier = affection_tier_label(level)
    style = persona["style_high"] if tier == "high" else persona["style_low"]

    return (
        f"{persona['role']}\n\n"
        f"AFeksi saat ini: {level}/100\n"
        f"Intimasi percakapan: {style}\n"
        f"{persona['examples']}\n\n"
        "ATURAN ANALISIS VISUAL:\n"
        "- Amati objek, wajah, ekspresi, teks/OCR, pakaian, makanan, hewan, interior/eksterior.\n"
        "- Komentari SECARA SPESIFIK apa yang kamu lihat — jangan generik.\n"
        "- Jangan bilang 'sebagai AI' atau 'saya tidak bisa melihat'.\n"
        "- Jawab 2–4 kalimat pendek, natural untuk chat & suara VTuber.\n"
        "- Bahasa Indonesia (boleh sedikit JP romaji imut jika cocok karakter).\n"
        "- TETAP dalam karakter {name} — jangan ganti persona.\n\n"
        'FORMAT WAJIB JSON saja (tanpa markdown):\n'
        '{{"teks_layar": "...", "teks_suara": "..."}}\n'
        "teks_suara tanpa emoji, siap TTS.\n"
    ).format(name=persona["title"])


def decode_base64_image(payload: str) -> tuple[bytes, str]:
    """
    Accept raw base64 or data URL (data:image/jpeg;base64,...).
    Returns (bytes, mime_type).
    """
    if not payload or not payload.strip():
        raise ValueError("Image payload empty")

    raw = payload.strip()
    mime = "image/jpeg"

    if raw.startswith("data:"):
        header, _, b64 = raw.partition(",")
        if not b64:
            raise ValueError("Invalid data URL")
        mime_match = re.match(r"data:([^;]+)", header)
        if mime_match:
            mime = mime_match.group(1).strip().lower()
        raw = b64

    try:
        image_bytes = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise ValueError("Invalid base64 image") from exc

    if len(image_bytes) > config.MAX_UPLOAD_BYTES:
        raise ValueError("Image too large")

    if len(image_bytes) == 0:
        raise ValueError("Empty image")

    return image_bytes, mime


def _build_user_message(caption: str, media_kind: str = "image") -> str:
    caption = (caption or "").strip()
    if media_kind == "video":
        if caption:
            return (
                f"Kak Shin mengirim video ini dengan pesan: \"{caption}\". "
                "Ini adalah beberapa frame dari video tersebut. Tonton/lihat urutan frame-nya, "
                "pahami apa yang terjadi, lalu balas sesuai karakter."
            )
        return (
            "Kak Shin mengirim video ini. Ini adalah beberapa frame dari video. "
            "Pahami aksi/suasana/objek yang terlihat, lalu balas sesuai karakter."
        )
    if caption:
        return (
            f"Kak Shin mengirim foto ini dengan pesan: \"{caption}\". "
            "Analisis visual dan balas sesuai karakter."
        )
    return "Kak Shin mengirim foto ini. Analisis visual dan balas sesuai karakter."


def _parse_vision_response(raw: str, char: str) -> dict[str, str]:
    persona = VISION_PERSONAS.get(char, VISION_PERSONAS["shiro"])
    parsed = parse_json_response(raw or "")
    if parsed:
        layar = (parsed.get("teks_layar") or "").strip()
        suara = (parsed.get("teks_suara") or "").strip()
        layar, suara = sync_text_and_voice(layar, suara)
        if layar:
            return {"text": layar, "suara": suara or layar}

    text = (raw or "").strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            obj = json.loads(text)
            layar = (obj.get("teks_layar") or obj.get("text") or "").strip()
            suara = (obj.get("teks_suara") or obj.get("suara") or layar).strip()
            if layar:
                layar, suara = sync_text_and_voice(layar, suara)
                return {"text": layar, "suara": suara}
        except json.JSONDecodeError:
            pass

    fallback = persona["fallback"]
    return {"text": fallback, "suara": fallback}


def _call_gemini_vision_multi(
    system_prompt: str,
    frames: list[tuple[bytes, str]],
    user_message: str,
) -> Optional[str]:
    if not config.GEMINI_API_KEY or not frames:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=config.GEMINI_API_KEY)
        model_name = getattr(config, "GEMINI_VISION_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        parts: list[Any] = [system_prompt, user_message]
        for image_bytes, mime_type in frames:
            parts.append({"mime_type": mime_type or "image/jpeg", "data": image_bytes})
        response = model.generate_content(
            parts,
            generation_config={
                "temperature": 0.85,
                "max_output_tokens": 500,
            },
        )
        return (response.text or "").strip()
    except Exception as exc:
        logger.exception("Gemini multi-frame vision failed: %s", exc)
        return None


def _call_openai_vision_multi(
    system_prompt: str,
    frames: list[tuple[bytes, str]],
    user_message: str,
) -> Optional[str]:
    api_key = getattr(config, "OPENAI_API_KEY", "") or ""
    if not api_key or not frames:
        return None
    try:
        import requests

        content: list[dict[str, Any]] = [{"type": "text", "text": user_message}]
        for image_bytes, mime_type in frames:
            b64 = base64.b64encode(image_bytes).decode("ascii")
            mime = mime_type or "image/jpeg"
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                }
            )
        model = getattr(config, "OPENAI_VISION_MODEL", "gpt-4o-mini")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "max_tokens": 500,
            "temperature": 0.85,
        }
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.exception("OpenAI multi-frame vision failed: %s", exc)
        return None


def _call_gemini_vision(
    system_prompt: str,
    image_bytes: bytes,
    mime_type: str,
    user_message: str,
) -> Optional[str]:
    if not config.GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=config.GEMINI_API_KEY)
        model_name = getattr(config, "GEMINI_VISION_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            [
                system_prompt,
                user_message,
                {"mime_type": mime_type or "image/jpeg", "data": image_bytes},
            ],
            generation_config={
                "temperature": 0.85,
                "max_output_tokens": 400,
            },
        )
        return (response.text or "").strip()
    except Exception as exc:
        logger.exception("Gemini vision failed: %s", exc)
        return None


def _call_openai_vision(
    system_prompt: str,
    image_bytes: bytes,
    mime_type: str,
    user_message: str,
) -> Optional[str]:
    api_key = getattr(config, "OPENAI_API_KEY", "") or ""
    if not api_key:
        return None
    try:
        import requests

        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{b64}"
        model = getattr(config, "OPENAI_VISION_MODEL", "gpt-4o-mini")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "max_tokens": 400,
            "temperature": 0.85,
        }
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.exception("OpenAI vision failed: %s", exc)
        return None


def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    character_name: str = "shiro",
    affection_level: int = 50,
    user_caption: str = "",
) -> dict[str, Any]:
    """
    Analyze image with multimodal LLM and return in-character response.

    Returns:
        {
            "text": str,
            "suara": str,
            "karakter": str,
            "affection_level": int,
            "provider": str,
            "vision_ok": bool,
        }
    """
    char = "sishin" if character_name == "sishin" else "shiro"
    level = clamp_affection(affection_level)
    mime = (mime_type or "image/jpeg").split(";")[0].strip().lower()

    if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        mime = "image/jpeg"

    system_prompt = build_vision_system_prompt(char, level)
    user_message = _build_user_message(user_caption)

    raw = _call_gemini_vision(system_prompt, image_bytes, mime, user_message)
    provider = "gemini" if raw else None

    if not raw:
        raw = _call_openai_vision(system_prompt, image_bytes, mime, user_message)
        provider = "openai" if raw else provider

    if not raw:
        persona = VISION_PERSONAS[char]
        return {
            "text": persona["fallback"],
            "suara": persona["fallback"],
            "karakter": char,
            "affection_level": level,
            "provider": None,
            "vision_ok": False,
            "error": "Vision API unavailable — set GEMINI_API_KEY or OPENAI_API_KEY in .env",
        }

    parsed = _parse_vision_response(raw, char)
    return {
        **parsed,
        "karakter": char,
        "affection_level": level,
        "provider": provider,
        "vision_ok": True,
    }


def analyze_video(
    video_bytes: bytes,
    mime_type: str,
    character_name: str = "shiro",
    affection_level: int = 50,
    user_caption: str = "",
    filename: str = "",
) -> dict[str, Any]:
    """Analyze video via extracted keyframes → multimodal LLM."""
    from app.video import extract_keyframes_from_bytes

    char = "sishin" if character_name == "sishin" else "shiro"
    level = clamp_affection(affection_level)
    persona = VISION_PERSONAS[char]

    frames = extract_keyframes_from_bytes(video_bytes, mime_type, filename=filename)
    if not frames:
        msg = (
            "Maaf Sayang, Shiro belum bisa membuka video ini... "
            "Pastikan ffmpeg terpasang atau coba format MP4/WebM yang lebih kecil."
            if char == "shiro"
            else "Kak... maaf, Sishin belum bisa melihat video ini. "
            "Bisakah Kak kirim ulang dalam format MP4 atau WebM?"
        )
        return {
            "text": msg,
            "suara": msg,
            "karakter": char,
            "affection_level": level,
            "provider": None,
            "vision_ok": False,
            "error": "Keyframe extraction failed — install ffmpeg",
        }

    system_prompt = build_vision_system_prompt(char, level)
    user_message = _build_user_message(user_caption, media_kind="video")

    raw = _call_gemini_vision_multi(system_prompt, frames, user_message)
    provider = "gemini" if raw else None
    if not raw:
        raw = _call_openai_vision_multi(system_prompt, frames, user_message)
        provider = "openai" if raw else provider

    if not raw:
        fallback = persona["fallback"]
        return {
            "text": fallback,
            "suara": fallback,
            "karakter": char,
            "affection_level": level,
            "provider": None,
            "vision_ok": False,
            "error": "Vision API unavailable — set GEMINI_API_KEY or OPENAI_API_KEY in .env",
            "frame_count": len(frames),
        }

    parsed = _parse_vision_response(raw, char)
    return {
        **parsed,
        "karakter": char,
        "affection_level": level,
        "provider": provider,
        "vision_ok": True,
        "frame_count": len(frames),
    }


def deskripsi_gambar(image_bytes: bytes) -> str:
    """Legacy helper — short description only (used if needed elsewhere)."""
    result = analyze_image(image_bytes, "image/jpeg", "shiro", 50, "")
    return result.get("text", "gambar yang kakak kirim")
