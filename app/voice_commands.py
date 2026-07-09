"""
Voice-command app launcher for Shiro AI (Windows).

Flow: transcript -> intent parse -> whitelist lookup -> subprocess launch -> character callback.

Security: built-in whitelist + PC scan + user folder app/data/user_apps/tambah_di_sini/
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import glob
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Callable, Optional

from app.app_catalog import (
    get_merged_registry,
    list_catalog_items,
    rescan_catalog,
    resolve_catalog_key,
    resolve_catalog_path,
)

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
        rf"(?:{_OPEN_VERBS})\s+(?:aplikasi\s+|app\s+|program\s+|software\s+)?(?P<app>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:{_OPEN_VERBS})\s+(?:the\s+)?(?:app\s+|application\s+)?(?P<app>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:bisakah|bisa|minta)\s+(?:kamu\s+|kalian\s+)?(?:tolong\s+)?"
        rf"(?:{_OPEN_VERBS})\s+(?:aplikasi\s+|app\s+|program\s+)?(?P<app>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?P<app>.+?)\s+(?:dong|deh|ya|nih|please|pls)\s*$",
        re.IGNORECASE,
    ),
]

_TRAILING_POLITENESS = re.compile(
    r"\s+(?:dong|deh|ya|yah|nih|please|pls|kak|sayang|teman)\s*$",
    re.IGNORECASE,
)

_registry_paths_cache: Optional[dict[str, str]] = None

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
    return get_merged_registry()


def _build_alias_index(registry: dict[str, dict]) -> dict[str, str]:
    from app.app_catalog import build_alias_index
    return build_alias_index(registry)


def normalize_transcript(text: str) -> str:
    """Strip wake words / character names from the start of a voice utterance."""
    t = (text or "").strip()
    t = re.sub(_CHAR_PREFIX, "", t, flags=re.IGNORECASE).strip()
    for _ in range(3):
        prev = t
        t = re.sub(_WAKE_PREFIX, "", t, flags=re.IGNORECASE).strip()
        t = re.sub(
            r"^(?:bisakah|bisa|minta)\s+(?:kamu\s+|kalian\s+)?(?:tolong\s+)?",
            "",
            t,
            flags=re.IGNORECASE,
        ).strip()
        if t == prev:
            break
    return t


def _clean_app_query(app_query: str) -> str:
    q = (app_query or "").strip(" .,!?:;\"'")
    q = _TRAILING_POLITENESS.sub("", q).strip()
    q = re.sub(r"^(?:aplikasi|app|program|software)\s+", "", q, flags=re.IGNORECASE).strip()
    return q


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
        app_query = _clean_app_query(match.group("app") or "")
        if len(app_query) < 2:
            continue
        has_open_verb = bool(re.search(_OPEN_VERBS, cleaned, re.IGNORECASE))
        has_polite_tail = bool(re.search(r"\b(dong|deh|please|pls)\s*$", cleaned, re.IGNORECASE))
        if not has_open_verb:
            if not has_polite_tail or len(app_query.split()) > 4:
                continue
        return LaunchIntent(raw_text=text, app_query=app_query, karakter=karakter)

    return None


def resolve_app_key(app_query: str, registry: Optional[dict] = None) -> tuple[Optional[str], float]:
    """Map user-spoken app name to registry key (exact + fuzzy)."""
    return resolve_catalog_key(app_query, registry or get_merged_registry())


def _load_registry_app_paths() -> dict[str, str]:
    """Build alias -> exe path map from Windows App Paths registry."""
    global _registry_paths_cache
    if _registry_paths_cache is not None:
        return _registry_paths_cache

    index: dict[str, str] = {}
    if sys.platform != "win32":
        _registry_paths_cache = index
        return index

    try:
        import winreg
    except ImportError:
        _registry_paths_cache = index
        return index

    subkeys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
    ]
    for hive, sub in subkeys:
        try:
            with winreg.OpenKey(hive, sub) as root:
                count = winreg.QueryInfoKey(root)[0]
                for i in range(count):
                    try:
                        exe_name = winreg.EnumKey(root, i)
                        with winreg.OpenKey(root, exe_name) as app_key:
                            path, _ = winreg.QueryValueEx(app_key, "")
                        path = (path or "").strip().strip('"')
                        if not path or not os.path.isfile(path):
                            continue
                        base = exe_name.lower()
                        stem = base[:-4] if base.endswith(".exe") else base
                        index[base] = path
                        index[stem] = path
                        label = stem.replace("_", " ").replace("-", " ")
                        if label and label not in index:
                            index[label] = path
                    except OSError:
                        continue
        except OSError:
            continue

    _registry_paths_cache = index
    return index


def _resolve_registry_exe(app_query: str) -> tuple[Optional[str], float]:
    """Find installed app exe via Windows registry App Paths."""
    reg = _load_registry_app_paths()
    if not reg:
        return None, 0.0

    query = app_query.lower().strip()
    if query in reg:
        return reg[query], 1.0

    query_exe = query if query.endswith(".exe") else query + ".exe"
    if query_exe in reg:
        return reg[query_exe], 1.0

    for alias, path in sorted(reg.items(), key=lambda x: -len(x[0])):
        if len(alias) < 3:
            continue
        if alias in query or query in alias:
            return path, 0.9

    keys = list(reg.keys())
    matches = get_close_matches(query, keys, n=1, cutoff=0.58)
    if matches:
        return reg[matches[0]], 0.72

    return None, 0.0


def _resolve_executable(entry: dict[str, Any]) -> Optional[str]:
    return resolve_catalog_path(entry)


def _is_blocked(entry: dict[str, Any], exe_path: str) -> bool:
    exe_name = os.path.basename(exe_path or entry.get("exe") or "").lower()
    return exe_name in _BLOCKED_EXES


def _spawn_exe(exe_path: str, entry: Optional[dict[str, Any]] = None) -> None:
    entry = entry or {}
    item_type = entry.get("type", "app")
    if item_type in ("file", "folder") or os.path.isdir(exe_path):
        os.startfile(exe_path)  # noqa: S606
        return
    if entry.get("use_startfile") or exe_path.startswith("ms-"):
        os.startfile(exe_path)  # noqa: S606
        return
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


def launch_application(app_query: str) -> LaunchResult:
    """
    Securely launch a catalog item (app, file, or folder) on Windows.
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
    entry: Optional[dict[str, Any]] = None
    exe_path: Optional[str] = None
    app_label = app_query.title()

    if app_key:
        entry = registry[app_key]
        app_label = entry.get("label") or app_key.title()
        exe_path = _resolve_executable(entry)

    if not exe_path:
        reg_path, reg_conf = _resolve_registry_exe(app_query)
        if reg_path:
            exe_path = reg_path
            confidence = max(confidence, reg_conf)
            if not app_key:
                app_label = app_query.title()
                app_key = os.path.splitext(os.path.basename(reg_path))[0].lower()

    if not exe_path:
        return LaunchResult(
            ok=False,
            status="not_found",
            app_label=app_label,
            message=f"Aplikasi '{app_query}' tidak ditemukan di PC ini. Taruh shortcut di app/data/user_apps/tambah_di_sini/",
            meta={"confidence": confidence},
        )

    if _is_blocked(entry or {}, exe_path):
        return LaunchResult(
            ok=False,
            status="blocked",
            app_key=app_key,
            app_label=app_label,
            exe_path=exe_path,
            message=f"{app_label} diblokir demi keamanan.",
        )

    try:
        _spawn_exe(exe_path, entry)
        logger.info("Launched app %s via %s", app_key or app_label, exe_path)
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
    if re.search(r"scan\s+ulang|perbarui\s+daftar|refresh\s+apps?", text, re.IGNORECASE):
        stats = rescan_catalog()
        result = LaunchResult(
            ok=True,
            status="success",
            app_label="katalog aplikasi",
            message=f"Scan selesai: {stats.get('total', 0)} item ditemukan.",
            meta=stats,
        )
        result.karakter = karakter
        return build_character_callback(result, karakter)

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
    """Apps, files, and folders in the merged catalog."""
    return list_catalog_items(limit=800)
