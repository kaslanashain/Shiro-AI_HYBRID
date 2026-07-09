"""
Laplace-style companion features: presence camera + music reactions.
"""
from __future__ import annotations

from typing import Any

from app.chat import jawab_shiro
from app.vision import analyze_image


PRESENCE_CAPTION = (
    "[MODE PRESENSI KAMERA] Kamu melihat Kakak lewat kamera desktop secara langsung "
    "(bukan foto upload). Komentari apa yang terlihat — wajah, ekspresi, objek di meja, "
    "cahaya ruangan — secara singkat dan natural seperti companion yang hidup di samping Kakak. "
    "Maksimal 2 kalimat. Jangan bilang kamu AI."
)


def analyze_presence_frame(
    image_bytes: bytes,
    mime_type: str,
    character_name: str = "shiro",
    affection_level: int = 50,
) -> dict[str, Any]:
    """Vision analysis tuned for always-on desktop camera presence."""
    return analyze_image(
        image_bytes,
        mime_type,
        character_name=character_name,
        affection_level=affection_level,
        user_caption=PRESENCE_CAPTION,
    )


def music_companion_reply(
    track_name: str,
    karakter: str = "shiro",
    mode: str = "opinion",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
  Music co-listening: character opinion or short original 'sing' lines.
  Returns (reply_data, status) like jawab_shiro.
  """
    track = (track_name or "lagu ini").strip()
    if mode == "sing":
        prompt = (
            f"[MODE MUSIK — NYANYI] Lagu yang diputar: «{track}». "
            "Nyanyikan 2–4 baris lirik pendek ORIGINAL (bukan lirik lagu asli) "
            "dalam gaya karaktermu, manja dan natural. Hanya lirik, tanpa penjelasan."
        )
    else:
        prompt = (
            f"[MODE MUSIK — PENDAPAT] Lagu yang sedang diputar bareng Kakak: «{track}». "
            "Beri pendapat singkat 1–2 kalimat — suka/tidak, vibe-nya, kenapa cocok atau tidak. "
            "Seperti teman yang dengerin musik bersama."
        )
    return jawab_shiro(prompt, preferred_karakter=karakter, force_preferred=True)
