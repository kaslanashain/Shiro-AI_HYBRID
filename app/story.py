"""Interactive Story Mode — AI sebagai Dungeon Master."""
import json
import logging
import random

from app.chat import _call_llm, CHARACTER_PROFILES
from app.db import story_create, story_get, story_get_active, story_update
from app.utils import parse_json_response

logger = logging.getLogger(__name__)

STORY_THEMES = {
    "fantasy": "Dunia fantasy dengan sihir, goblin, dan kastil kuno.",
    "school": "Sekolah ajaib di Jepang dengan misteri dan persahabatan.",
    "space": "Petualangan antar bintang dengan robot dan planet alien.",
    "cozy": "Petualangan santai di desa kecil dengan teka-teki ringan.",
}

DM_BASE = (
    "Kamu adalah Dungeon Master (DM) untuk petualangan roleplay interaktif.\n"
    "Companion pemain: {companion_name} ({companion_desc}).\n"
    "Tema: {theme}\n"
    "Lokasi saat ini: {location}\n"
    "HP pemain: {hp}/100\n"
    "Inventory: {inventory}\n\n"
    "ATURAN DM:\n"
    "- Gambarkan scene vivid dalam 2-4 kalimat (bahasa Indonesia)\n"
    "- Berikan 2-3 pilihan aksi konkret di field choices\n"
    "- Update hp jika ada bahaya (-5 sampai -25) atau healing (+5 sampai +15)\n"
    "- Companion ({companion_name}) boleh komen singkat in-character di narration\n"
    "- Nyambung dengan scene sebelumnya — jangan reset cerita\n\n"
    "RIWAYAT:\n{history}\n\n"
    'FORMAT WAJIB JSON:\n'
    '{{"narration": "...", "choices": ["...", "..."], "hp_delta": 0, '
    '"location": "...", "companion_line": "..."}}'
)


def _companion_info(karakter):
    if karakter == "sishin":
        return "Sishin", "adik imut yang ikut petualangan dan suka hore-hore"
    return "Shiro", "waifu manja yang melindungi pemain dengan sayang"


def _parse_history(raw):
    try:
        return json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []


def start_story(karakter="shiro", theme="fantasy", title=None):
    karakter = karakter if karakter in ("shiro", "sishin") else "shiro"
    theme = theme if theme in STORY_THEMES else "fantasy"
    title = title or f"Petualangan {STORY_THEMES[theme][:20]}..."

    session_id = story_create(karakter=karakter, title=title)
    opening_action = "Mulai petualangan baru. Perkenalkan dunia dan situasi awal yang menarik."

    result = process_story_action(session_id, opening_action, karakter, theme, is_start=True)
    result["session_id"] = session_id
    result["theme"] = theme
    result["title"] = title
    return result


def process_story_action(session_id, action, karakter=None, theme="fantasy", is_start=False):
    session = story_get(session_id)
    if not session:
        return {"error": "Sesi story tidak ditemukan"}

    karakter = karakter or session.get("karakter", "shiro")
    companion_name, companion_desc = _companion_info(karakter)
    history = _parse_history(session.get("history"))
    if not is_start:
        history.append({"role": "user", "content": action})
    history = history[-12:]

    history_text = "\n".join(
        f"{'Pemain' if h['role'] == 'user' else 'DM'}: {h['content']}"
        for h in history
    ) or "(awal petualangan)"

    try:
        inventory = json.loads(session.get("inventory") or "[]")
    except json.JSONDecodeError:
        inventory = []

    system = DM_BASE.format(
        companion_name=companion_name,
        companion_desc=companion_desc,
        theme=STORY_THEMES.get(theme, STORY_THEMES["fantasy"]),
        location=session.get("location", "Desa Awal"),
        hp=session.get("hp", 100),
        inventory=", ".join(inventory) if inventory else "kosong",
        history=history_text,
    )

    user_msg = action if not is_start else "Buka petualangan dengan scene pembuka yang epik."

    try:
        response = _call_llm([
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ])
        raw = response["message"]["content"]
    except Exception as exc:
        logger.exception("Story LLM failed: %s", exc)
        return {"error": "Gagal generate cerita"}

    parsed = parse_json_response(raw)
    if not parsed:
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end > start:
                obj = json.loads(raw[start : end + 1])
                if obj.get("narration"):
                    parsed = obj
        except json.JSONDecodeError:
            parsed = None

    if not parsed:
        narration = raw.strip()[:600]
        choices = ["Lanjutkan", "Periksa sekitar", "Bicara dengan companion"]
        hp_delta = 0
        location = session.get("location", "Desa Awal")
        companion_line = ""
    else:
        narration = parsed.get("narration", "").strip()
        choices = parsed.get("choices", [])[:4]
        hp_delta = int(parsed.get("hp_delta", 0) or 0)
        location = parsed.get("location", session.get("location", "Desa Awal"))
        companion_line = parsed.get("companion_line", "").strip()

    if not narration:
        narration = "Angin berhembus... petualanganmu belum berakhir."

    if not choices:
        choices = ["Jelajahi", "Istirahat", "Bicara"]

    new_hp = max(0, min(100, session.get("hp", 100) + hp_delta))
    dm_entry = narration
    if companion_line:
        dm_entry += f"\n\n{companion_name}: {companion_line}"

    history.append({"role": "assistant", "content": dm_entry})
    story_update(
        session_id,
        location=location,
        hp=new_hp,
        scene=narration,
        history=json.dumps(history, ensure_ascii=False),
    )

    profile = CHARACTER_PROFILES.get(karakter, CHARACTER_PROFILES["shiro"])
    return {
        "session_id": session_id,
        "narration": narration,
        "companion_line": companion_line,
        "companion_name": companion_name,
        "choices": choices,
        "hp": new_hp,
        "location": location,
        "karakter": karakter,
        "game_over": new_hp <= 0,
    }


def get_active_story(karakter="shiro"):
    session = story_get_active(karakter=karakter)
    if not session:
        return None
    history = _parse_history(session.get("history"))
    last = history[-1]["content"] if history else session.get("scene", "")
    return {
        "session_id": session["id"],
        "title": session.get("title"),
        "hp": session.get("hp", 100),
        "location": session.get("location"),
        "last_scene": last,
        "karakter": session.get("karakter", karakter),
    }
