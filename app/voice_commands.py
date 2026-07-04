"""
Voice-command app launcher for Shiro AI (Windows).

Flow: transcript -> intent parse -> whitelist lookup -> subprocess launch -> character callback.

Security: only apps listed in app/data/windows_apps.json may be launched; no shell=True;
executable paths must resolve from the registry — arbitrary user paths are rejected.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parent / "data" / "windows_apps.json"

# Indonesian + English open-app triggers
_OPEN_VERBS = (
    r"buka|bukain|bukain|jalankan|nyalakan|luncurkan|start|open|launch|run|startkan"
)
_WAKE_PREFIX = (
    r"^(?:hey|hei|hai|ok|okay|tolong|please|can you|could you)[,\s]+"
)
_CHAR_PREFIX = r"^(?:shiro|sishin|siro|sisin)[,\s\-]+"

_OPEN_PATTERNS = [
    re.compile(
        rf"(?:{_OPEN_VERBS})\s+(?:aplikasi\s+|app\s+|program\s+)?(?P<app>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:{_OPEN_VERBS})\s+(?:the\s+)?(?:app\s+|application\s+)?(?P<app>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?P<app>.+?)\s+(?:dong|deh|ya|please|pls)\s*$",
        re.IGNORECASE,
    ),
]

_BLOCKED_EXES = frozenset(
    {
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",
        "wscript.exe",
        "cscript.exe",
        "mshta.exe",
        "reg.exe",
        "format.com",
    }
)

CHARACTER_CALLBACKS = {
    "shiro": {
        "success": "Baik Sayang~ aku bukakan {app_label} ya! Semoga lancar~",
        "not_found": "Hmm... Shiro nggak nemu aplikasi {app_label} di komputer Kakak Shin. Coba sebut nama lain?",
        "blocked": "Sayang, Shiro nggak boleh buka {app_label} demi keamanan komputer Kakak~",
        "error": "Maaf Sayang, ada masalah waktu mau buka {app_label}... coba lagi ya~",
        "no_intent": "",
    },
    "sishin": {
        "success": "Oke Kak! {app_label} sudah dibuka~ hore!",
        "not_found": "Kak, Sishin nggak ketemu aplikasi {app_label} nih... namanya bener?",
        "blocked": "Kak, Sishin nggak boleh buka {app_label} — bahaya buat komputer~",
        "error": "Kak, Sishin gagal buka {app_label}... coba lagi ya~",
        "no_intent": "",
    },
}


@dataclass
class LaunchIntent:
    raw_text: str
    app_query: str
    karakter: str = "shiro"


@dataclass
class LaunchResult:
    ok: bool
    status: str  # success | not_found | blocked | error | no_intent
    app_key: str = ""
    app_label: str = ""
    exe_path: str = ""
    message: str = ""
    text: str = ""
    suara: str = ""
    karakter: str = "shiro"
    meta: dict = field(default_factory=dict)


def _expand_path(path: str) -> str:
    expanded = os.path.expandvars(path)
    return os.path.expanduser(expanded)


def _load_app_registry() -> dict[str, dict[str, Any]]:
    if not _DATA_PATH.is_file():
        logger.warning("App registry missing: %s", _DATA_PATH)
        return {}
    with open(_DATA_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def _build_alias_index(registry: dict[str, dict]) -> dict[str, str]:
    index: dict[str, str] = {}
    for key, entry in registry.items():
        index[key.lower()] = key
        label = (entry.get("label") or key).lower()
        index[label] = key
        for alias in entry.get("aliases") or []:
            if alias:
                index[str(alias).lower()] = key
    return index


def normalize_transcript(text: str) -> str:
    """Strip wake words / character names from the start of a voice utterance."""
    t = (text or "").strip()
    t = re.sub(_CHAR_PREFIX, "", t, flags=re.IGNORECASE).strip()
    t = re.sub(_WAKE_PREFIX, "", t, flags=re.IGNORECASE).strip()
    return t


def parse_launch_intent(text: str, karakter: str = "shiro") -> Optional[LaunchIntent]:
    """
    Detect open-app intent in Indonesian or English.
    Returns LaunchIntent or None if not an app-launch command.
    """
    cleaned = normalize_transcript(text)
    if not cleaned:
        return None

    for pattern in _OPEN_PATTERNS:
        match = pattern.search(cleaned)
        if not match:
            continue
        app_query = (match.group("app") or "").strip(" .,!?:;\"'")
        if len(app_query) < 2:
            continue
        return LaunchIntent(raw_text=text, app_query=app_query, karakter=karakter)

    return None


def resolve_app_key(app_query: str, registry: Optional[dict] = None) -> tuple[Optional[str], float]:
    """Map user-spoken app name to registry key (exact + fuzzy)."""
    registry = registry or _load_app_registry()
    if not registry:
        return None, 0.0

    query = app_query.lower().strip()
    alias_index = _build_alias_index(registry)

    if query in alias_index:
        return alias_index[query], 1.0

    # Substring match (e.g. "google chrome browser" -> chrome)
    for alias, key in sorted(alias_index.items(), key=lambda x: -len(x[0])):
        if alias in query or query in alias:
            return key, 0.92

    keys = list(alias_index.keys())
    matches = get_close_matches(query, keys, n=1, cutoff=0.62)
    if matches:
        return alias_index[matches[0]], 0.75

    return None, 0.0


def _resolve_executable(entry: dict[str, Any]) -> Optional[str]:
    exe_name = entry.get("exe") or ""
    if not exe_name:
        return None

    if entry.get("use_startfile") and exe_name.startswith("ms-"):
        return exe_name

    for raw in entry.get("paths") or []:
        path = _expand_path(raw)
        if path and os.path.isfile(path):
            return path

    found = shutil.which(exe_name)
    if found and os.path.isfile(found):
        return found

    return None


def _is_blocked(entry: dict[str, Any], exe_path: str) -> bool:
    exe_name = os.path.basename(exe_path or entry.get("exe") or "").lower()
    return exe_name in _BLOCKED_EXES


def launch_application(app_query: str) -> LaunchResult:
    """
    Securely launch a whitelisted Windows application.
    Only works on Windows; returns not_found on other OS.
    """
    if sys.platform != "win32":
        return LaunchResult(
            ok=False,
            status="error",
            app_label=app_query,
            message="App launcher hanya tersedia di Windows.",
        )

    registry = _load_app_registry()
    app_key, confidence = resolve_app_key(app_query, registry)
    if not app_key:
        return LaunchResult(
            ok=False,
            status="not_found",
            app_label=app_query.title(),
            message=f"Aplikasi '{app_query}' tidak ada di whitelist.",
            meta={"confidence": confidence},
        )

    entry = registry[app_key]
    app_label = entry.get("label") or app_key.title()
    exe_path = _resolve_executable(entry)

    if not exe_path:
        return LaunchResult(
            ok=False,
            status="not_found",
            app_key=app_key,
            app_label=app_label,
            message=f"{app_label} terdaftar tapi tidak terpasang di PC ini.",
            meta={"confidence": confidence},
        )

    if _is_blocked(entry, exe_path):
        return LaunchResult(
            ok=False,
            status="blocked",
            app_key=app_key,
            app_label=app_label,
            exe_path=exe_path,
            message=f"{app_label} diblokir demi keamanan.",
        )

    try:
        if entry.get("use_startfile") or exe_path.startswith("ms-"):
            os.startfile(exe_path)  # noqa: S606 — Windows URI schemes e.g. ms-settings:
        else:
            args = [exe_path]
            extra = entry.get("launch_args") or []
            if extra:
                args.extend(extra)
            subprocess.Popen(  # noqa: S603
                args,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        logger.info("Launched app %s via %s", app_key, exe_path)
        return LaunchResult(
            ok=True,
            status="success",
            app_key=app_key,
            app_label=app_label,
            exe_path=exe_path,
            message=f"{app_label} launched.",
            meta={"confidence": confidence},
        )
    except OSError as exc:
        logger.exception("Launch failed for %s: %s", app_key, exc)
        return LaunchResult(
            ok=False,
            status="error",
            app_key=app_key,
            app_label=app_label,
            exe_path=exe_path,
            message=str(exc),
            meta={"confidence": confidence},
        )


def build_character_callback(result: LaunchResult, karakter: str = "shiro") -> LaunchResult:
    """Fill text/suara placeholders based on Shiro or Sishin personality."""
    karakter = "sishin" if karakter == "sishin" else "shiro"
    templates = CHARACTER_CALLBACKS[karakter]
    status = result.status if result.status in templates else "error"
    template = templates.get(status) or templates["error"]

    label = result.app_label or result.app_key or "aplikasi itu"
    spoken = template.format(app_label=label, app_key=result.app_key or label)

    result.karakter = karakter
    result.text = spoken
    result.suara = spoken
    return result


def process_launch_command(
    text: str,
    karakter: str = "shiro",
    *,
    on_callback: Optional[Callable[[LaunchResult], None]] = None,
) -> Optional[LaunchResult]:
    """
    Full pipeline: parse intent -> launch -> character response.
    Returns None if the utterance is not an app-launch command.
    """
    intent = parse_launch_intent(text, karakter)
    if not intent:
        return None

    launch = launch_application(intent.app_query)
    launch.karakter = karakter
    result = build_character_callback(launch, karakter)

    if on_callback:
        on_callback(result)

    return result


def list_available_apps() -> list[dict[str, str]]:
    """Apps in registry that appear installed on this machine."""
    registry = _load_app_registry()
    out = []
    for key, entry in registry.items():
        exe = _resolve_executable(entry)
        out.append(
            {
                "key": key,
                "label": entry.get("label") or key.title(),
                "installed": bool(exe),
            }
        )
    return sorted(out, key=lambda x: x["label"].lower())
