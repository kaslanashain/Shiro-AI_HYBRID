"""Konteks dunia nyata untuk Shiro & Sishin — waktu, cuaca, headline terkini."""
from __future__ import annotations

import logging
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Asia/Jakarta")

DAY_NAMES = (
    "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu",
)
MONTH_NAMES = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)

_weather_cache: dict[str, dict] = {}
_headlines_cache: dict | None = None
WEATHER_TTL = 600
HEADLINES_TTL = 1800


def get_now() -> datetime:
    return datetime.now(TZ)


def _day_period(hour: int) -> str:
    if 5 <= hour < 11:
        return "pagi"
    if 11 <= hour < 15:
        return "siang"
    if 15 <= hour < 18:
        return "sore"
    if 18 <= hour < 22:
        return "malam"
    return "tengah malam"


def weather_code_label(code: int) -> str:
    if code in (0, 1):
        return "cerah"
    if code == 2:
        return "sedikit berawan"
    if code == 3:
        return "berawan"
    if 45 <= code <= 48:
        return "berkabut"
    if 51 <= code <= 55:
        return "gerimis"
    if 61 <= code <= 65:
        return "hujan"
    if 71 <= code <= 75:
        return "salju"
    if 80 <= code <= 82:
        return "hujan deras"
    if 95 <= code <= 99:
        return "badai petir"
    return "tidak diketahui"


def fetch_weather(lat: str | float | None = None, lon: str | float | None = None) -> dict | None:
    lat = lat or os.environ.get("WEATHER_LAT", "-6.2088")
    lon = lon or os.environ.get("WEATHER_LON", "106.8456")
    city = os.environ.get("WEATHER_CITY", "Jakarta")
    cache_key = f"{lat},{lon}"
    now_ts = time.time()

    cached = _weather_cache.get(cache_key)
    if cached and now_ts - cached["ts"] < WEATHER_TTL:
        return cached["data"]

    try:
        url = (
            "https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current_weather=true&timezone=Asia%2FJakarta"
        )
        response = requests.get(url, timeout=8)
        if response.status_code != 200:
            raise RuntimeError(f"Open-Meteo status {response.status_code}")
        payload = response.json()
        current = payload.get("current_weather") or {}
        code = int(current.get("weathercode", -1))
        data = {
            "temperature": current.get("temperature"),
            "weathercode": code,
            "description": weather_code_label(code),
            "windspeed": current.get("windspeed"),
            "city": city,
        }
        _weather_cache[cache_key] = {"ts": now_ts, "data": data}
        return data
    except Exception as exc:
        logger.debug("Weather fetch failed: %s", exc)
        if cached:
            return cached["data"]
        return None


def fetch_headlines(limit: int = 3) -> list[str]:
    global _headlines_cache
    now_ts = time.time()
    if (
        _headlines_cache
        and now_ts - _headlines_cache.get("ts", 0) < HEADLINES_TTL
    ):
        return list(_headlines_cache.get("items", []))

    items: list[str] = []
    try:
        url = "https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id"
        response = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "ShiroAI/1.0"},
        )
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item")[:limit]:
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    title = title_el.text.strip()
                    if title and title not in items:
                        items.append(title)
    except Exception as exc:
        logger.debug("Headlines fetch failed: %s", exc)
        if _headlines_cache:
            return list(_headlines_cache.get("items", []))

    _headlines_cache = {"ts": now_ts, "items": items}
    return items


def format_world_context_block(karakter: str | None = None) -> str:
    """Blok teks untuk system prompt — Shiro/Sishin tahu waktu & cuaca saat ini."""
    now = get_now()
    day = DAY_NAMES[now.weekday()]
    month = MONTH_NAMES[now.month - 1]
    period = _day_period(now.hour)

    lines = [
        "INFORMASI DUNIA NYATA SAAT INI (kamu BENAR-BENAR tahu ini — sebut natural jika relevan):",
        (
            f"- Waktu: {day}, {now.day} {month} {now.year}, "
            f"pukul {now.strftime('%H:%M')} WIB ({period})"
        ),
    ]

    weather = fetch_weather()
    if weather and weather.get("temperature") is not None:
        city = weather.get("city", "Jakarta")
        temp = weather["temperature"]
        desc = weather.get("description", "")
        wind = weather.get("windspeed")
        wind_part = f", angin {wind} km/j" if wind is not None else ""
        lines.append(f"- Cuaca di {city}: {temp}°C, {desc}{wind_part}")

    headlines = fetch_headlines()
    if headlines:
        lines.append("- Kabar terkini (Indonesia):")
        for headline in headlines:
            lines.append(f"  • {headline}")

    lines.append(
        "- Kamu BOLEH dan DIPERSILAKAN menyebut jam, tanggal, tahun, cuaca, atau berita "
        "jika cocok dengan obrolan — jangan bilang kamu tidak tahu waktu/cuaca."
    )

    if karakter == "sishin":
        lines.append(
            "- Gaya Sishin: 'Kak, hari ini panas banget ya~' atau "
            "'Udah jam segini lho, Kak jangan begadang~'"
        )
    elif karakter == "shiro":
        lines.append(
            "- Gaya Shiro: 'Sayang, di luar gerimis nih~ stay warm ya' atau "
            "'Sudah larut, Sayang istirahat dulu~'"
        )

    return "\n".join(lines) + "\n\n"


def world_context_for_validation() -> str:
    """Ringkasan singkat agar validasi respons mengizinkan fakta waktu/cuaca."""
    now = get_now()
    month = MONTH_NAMES[now.month - 1]
    parts = [
        f"tanggal {now.day} {month} {now.year}",
        f"tahun {now.year}",
        f"jam {now.strftime('%H:%M')} WIB",
        "cuaca",
        "informasi dunia nyata",
    ]
    weather = fetch_weather()
    if weather:
        parts.append(str(weather.get("temperature", "")))
        parts.append(weather.get("description", ""))
    for headline in fetch_headlines():
        parts.append(headline.lower())
    return " ".join(parts)
