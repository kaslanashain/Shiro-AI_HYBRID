"""
Voice-command app launcher for Shiro AI (Windows).

Flow: STT text → intent parse → whitelist lookup → subprocess launch → character callback.

Security: only apps in WINDOWS_APPS catalog may launch; shell=False; no user shell strings.
"""
from __future__ import annotations

import difflib
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Windows app catalog (whitelist)
# keys = canonical id; aliases = fuzzy match terms (EN + ID)
# ---------------------------------------------------------------------------
WINDOWS_APPS: dict[str, dict[str, Any]] = {
    "notepad": {
        "label": "Notepad",
        "aliases": ["notepad", "catatan", "note pad", "notepad.exe"],
        "exe": "notepad.exe",
        "paths": [r"%SystemRoot%\System32\notepad.exe"],
    },
    "calculator": {
        "label": "Calculator",
        "aliases": ["calculator", "calc", "kalkulator", "calc.exe"],
        "exe": "calc.exe",
        "paths": [r"%SystemRoot%\System32\calc.exe"],
    },
    "chrome": {
        "label": "Google Chrome",
        "aliases": ["chrome", "google chrome", "chromium", "browser", "google"],
        "exe": "chrome.exe",
        "paths": [
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
        ],
    },
    "edge": {
        "label": "Microsoft Edge",
        "aliases": ["edge", "microsoft edge", "msedge"],
        "exe": "msedge.exe",
        "paths": [
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        ],
    },
    "firefox": {
        "label": "Mozilla Firefox",
        "aliases": ["firefox", "mozilla firefox"],
        "exe": "firefox.exe",
        "paths": [
            r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
            r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
        ],
    },
    "spotify": {
        "label": "Spotify",
        "aliases": ["spotify", "music spotify"],
        "exe": "Spotify.exe",
        "paths": [
            r"%AppData%\Spotify\Spotify.exe",
        ],
    },
    "discord": {
        "label": "Discord",
        "aliases": ["discord"],
        "exe": "Discord.exe",
        "paths": [
            r"%LocalAppData%\Discord\Update.exe",
            r"%LocalAppData%\Discord\app-*\Discord.exe",
        ],
        "args": ["--processStart", "Discord.exe"],
    },
    "vscode": {
        "label": "Visual Studio Code",
        "aliases": ["vscode", "vs code", "visual studio code", "code editor", "code"],
        "exe": "Code.exe",
        "paths": [
            r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe",
            r"%ProgramFiles%\Microsoft VS Code\Code.exe",
        ],
    },
    "explorer": {
        "label": "File Explorer",
        "aliases": ["explorer", "file explorer", "files", "folder", "explorer.exe", "penjelajah file"],
        "exe": "explorer.exe",
        "paths": [r"%SystemRoot%\explorer.exe"],
    },
    "cmd": {
        "label": "Command Prompt",
        "aliases": ["cmd", "command prompt", "terminal", "prompt"],
        "exe": "cmd.exe",
        "paths": [r"%SystemRoot%\System32\cmd.exe"],
    },
    "powershell": {
        "label": "PowerShell",
        "aliases": ["powershell", "pwsh", "power shell"],
        "exe": "powershell.exe",
        "paths": [r"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"],
    },
    "paint": {
        "label": "Paint",
        "aliases": ["paint", "mspaint", "microsoft paint", "cat"],
        "exe": "mspaint.exe",
        "paths": [r"%SystemRoot%\System32\mspaint.exe"],
    },
    "word": {
        "label": "Microsoft Word",
        "aliases": ["word", "microsoft word", "ms word"],
        "exe": "WINWORD.EXE",
        "paths": [
            r"%ProgramFiles%\Microsoft Office\root\Office16\WINWORD.EXE",
            r"%ProgramFiles(x86)%\Microsoft Office\root\Office16\WINWORD.EXE",
        ],
    },
    "excel": {
        "label": "Microsoft Excel",
        "aliases": ["excel", "microsoft excel", "spreadsheet"],
        "exe": "EXCEL.EXE",
        "paths": [
            r"%ProgramFiles%\Microsoft Office\root\Office16\EXCEL.EXE",
            r"%ProgramFiles(x86)%\Microsoft Office\root\Office16\EXCEL.EXE",
        ],
    },
    "steam": {
        "label": "Steam",
        "aliases": ["steam", "game steam"],
        "exe": "steam.exe",
        "paths": [
            r"%ProgramFiles(x86)%\Steam\steam.exe",
            r"%ProgramFiles%\Steam\steam.exe",
        ],
    },
    "obs": {
        "label": "OBS Studio",
        "aliases": ["obs", "obs studio", "streaming obs"],
        "exe": "obs64.exe",
        "paths": [
            r"%ProgramFiles%\obs-studio\bin\64bit\obs64.exe",
            r"%ProgramFiles(x86)%\obs-studio\bin\64bit\obs64.exe",
        ],
    },
    "whatsapp": {
        "label": "WhatsApp",
        "aliases": ["whatsapp", "wa", "whats app"],
        "exe": "WhatsApp.exe",
        "paths": [
            r"%LocalAppData%\WhatsApp\WhatsApp.exe",
        ],
    },
    "telegram": {
        "label": "Telegram",
        "aliases": ["telegram", "tele"],
        "exe": "Telegram.exe",
        "paths": [
            r"%AppData%\Telegram Desktop\Telegram.exe",
        ],
    },
}

# Wake words / character prefixes stripped before intent parse
WAKE_PREFIXES = (
    r"^(?:hey\s+|hai\s+|halo\s+)?(?:shiro|sishin|siro|sisin)(?:\s+chan|\s+kun)?[\s,:-]+",
    r"^(?:tolong\s+|please\s+|pls\s+|kindly\s+)",
)

# EN + ID launch intent patterns — group(1) = app name
LAUNCH_PATTERNS = [
    re.compile(
        r"(?:please\s+)?(?:open|launch|run|start|execute)\s+(?:the\s+|app(?:lication)?\s+)?(.+?)(?:[\s.?!,]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:tolong\s+)?(?:buka|bukaan|jalankan|nyalakan|luncurkan|start)\s+(?:aplikasi\s+|app\s+)?(.+?)(?:[\s.?!,]|$|(?:\s+dong)|(?:\s+ya)|(?:\s+nya))",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:bisa|bisakah|could you|can you)\s+(?:tolong\s+)?(?:buka|open)\s+(?:aplikasi\s+)?(.+?)(?:[\s.?!,]|$)",
        re.IGNORECASE,
    ),
]

TRAILING_FILLERS = re.compile(
    r"\s+(?:please|pls|dong|ya|yah|nih|deh|tuh|sekarang|now|thanks|thank you|makasih|terima kasih)$",
    re.IGNORECASE,
)

UNSAFE_CHARS = re.compile(r"[;&|`$<>]")

CHARACTER_RESPONSES = {
    "shiro": {
        "success": "Baik Sayang~ Shiro bukain {app} ya!",
        "success_suara": "Baik Sayang, Shiro bukain {app} ya",
        "not_found": "Maaf Sayang... Shiro nggak nemu aplikasi {app}. Coba sebut nama yang lebih jelas?",
        "not_found_suara": "Maaf Sayang, Shiro nggak nemu aplikasi {app}",
        "not_intent": "",
        "error": "Ups Sayang, ada masalah waktu mau buka {app}... coba lagi ya~",
        "error_suara": "Ups Sayang, ada masalah waktu mau buka {app}",
        "disabled": "Sayang, perintah buka aplikasi belum aktif di sistem ini~",
    },
    "sishin": {
        "success": "Oke Kak! Sishin bukain {app} nih~ hore!",
        "success_suara": "Oke Kak, Sishin bukain {app} nih",
        "not_found": "Kak... Sishin nggak ketemu aplikasi {app}. Coba bilang lagi ya?",
        "not_found_suara": "Kak, Sishin nggak ketemu aplikasi {app}",
        "not_intent": "",
        "error": "Kak, Sishin gagal buka {app}... coba lagi ya~",
        "error_suara": "Kak, Sishin gagal buka {app}",
        "disabled": "Kak, buka aplikasi lewat suara belum aktif di sini~",
    },
}


@dataclass
class LaunchIntent:
    raw_text: str
    app_query: str
    language_hint: str = "id"


@dataclass
class AppTarget:
    app_id: str
    label: str
    exe_path: str
    args: list[str] = field(default_factory=list)


@dataclass
class LaunchResult:
    handled: bool
    success: bool
    status: str  # success | not_found | error | not_intent | disabled
    app_label: str = ""
    app_id: str = ""
    message: str = ""
    suara: str = ""
    karakter: str = "shiro"
    raw_text: str = ""


def _expand_path(path: str) -> str:
    return os.path.expandvars(os.path.expanduser(path))


def _glob_first(pattern: str) -> str | None:
    import glob

    expanded = _expand_path(pattern)
    if "*" in expanded:
        matches = sorted(glob.glob(expanded))
        return matches[0] if matches else None
    return expanded if os.path.isfile(expanded) else None


def _normalize_query(text: str) -> str:
    t = (text or "").strip().lower()
    t = TRAILING_FILLERS.sub("", t).strip()
    t = re.sub(r"\s+", " ", t)
    return t


def _strip_wake_words(text: str) -> str:
    t = text.strip()
    for pat in WAKE_PREFIXES:
        t = re.sub(pat, "", t, flags=re.IGNORECASE).strip()
    return t


def parse_launch_intent(text: str) -> LaunchIntent | None:
    """
    Parse voice/text for app-launch intent (English + Indonesian).
    Returns None if the utterance is not a launch command.
    """
    if not text or not text.strip():
        return None

    cleaned = _strip_wake_words(text)
    if UNSAFE_CHARS.search(cleaned):
        logger.warning("Blocked unsafe characters in voice command")
        return None

    for pattern in LAUNCH_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            app_query = _normalize_query(match.group(1))
            if len(app_query) >= 2:
                lang = "en" if re.search(r"\b(open|launch|run|start|please)\b", cleaned, re.I) else "id"
                return LaunchIntent(raw_text=text.strip(), app_query=app_query, language_hint=lang)

    return None


def _build_alias_index() -> list[tuple[str, str, str]]:
    """Return [(alias, app_id, label), ...] sorted by alias length desc for greedy match."""
    rows: list[tuple[str, str, str]] = []
    for app_id, meta in WINDOWS_APPS.items():
        label = meta.get("label", app_id)
        for alias in meta.get("aliases", [app_id]):
            rows.append((_normalize_query(alias), app_id, label))
    rows.sort(key=lambda r: len(r[0]), reverse=True)
    return rows


_ALIAS_INDEX = _build_alias_index()


def resolve_app_target(query: str, cutoff: float = 0.72) -> AppTarget | None:
    """Map spoken app name to a whitelisted executable (exact → substring → fuzzy)."""
    q = _normalize_query(query)
    if not q or UNSAFE_CHARS.search(q):
        return None

    # Exact alias match
    for alias, app_id, label in _ALIAS_INDEX:
        if q == alias:
            path = _resolve_executable(WINDOWS_APPS[app_id])
            if path:
                return AppTarget(app_id, label, path, list(WINDOWS_APPS[app_id].get("args") or []))

    # Substring: query contained in alias or vice versa
    for alias, app_id, label in _ALIAS_INDEX:
        if q in alias or alias in q:
            path = _resolve_executable(WINDOWS_APPS[app_id])
            if path:
                return AppTarget(app_id, label, path, list(WINDOWS_APPS[app_id].get("args") or []))

    # Fuzzy match across all aliases
    all_aliases = [a[0] for a in _ALIAS_INDEX]
    close = difflib.get_close_matches(q, all_aliases, n=3, cutoff=cutoff)
    for match in close:
        for alias, app_id, label in _ALIAS_INDEX:
            if alias == match:
                path = _resolve_executable(WINDOWS_APPS[app_id])
                if path:
                    return AppTarget(app_id, label, path, list(WINDOWS_APPS[app_id].get("args") or []))

    return None


def _resolve_executable(meta: dict[str, Any]) -> str | None:
    """Find first existing executable path for a catalog entry."""
    for raw in meta.get("paths") or []:
        found = _glob_first(raw)
        if found and os.path.isfile(found):
            return found

    exe = meta.get("exe")
    if exe:
        which = shutil.which(exe)
        if which and os.path.isfile(which):
            return which

    return None


def launch_application(target: AppTarget) -> tuple[bool, str]:
    """
    Launch a whitelisted application on Windows (shell=False).
    Returns (success, error_message).
    """
    if os.name != "nt":
        return False, "App launcher only supported on Windows"

    if not target.exe_path or not os.path.isfile(target.exe_path):
        return False, "Executable not found"

    # Re-verify path is under allowed catalog entry
    allowed = _resolve_executable(WINDOWS_APPS.get(target.app_id, {}))
    if not allowed or os.path.normcase(allowed) != os.path.normcase(target.exe_path):
        return False, "Path not in whitelist"

    cmd = [target.exe_path] + (target.args or [])
    try:
        subprocess.Popen(
            cmd,
            shell=False,
            cwd=os.path.dirname(target.exe_path) or None,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        logger.info("Launched %s via %s", target.label, target.exe_path)
        return True, ""
    except OSError as exc:
        logger.exception("Launch failed for %s: %s", target.label, exc)
        return False, str(exc)


def build_character_response(
    result_status: str,
    karakter: str,
    app_label: str = "",
    app_query: str = "",
) -> tuple[str, str]:
    """Return (teks_layar, teks_suara) for Shiro or Sishin."""
    karakter = "sishin" if karakter == "sishin" else "shiro"
    templates = CHARACTER_RESPONSES[karakter]
    name = app_label or app_query or "aplikasi itu"

    key_map = {
        "success": ("success", "success_suara"),
        "not_found": ("not_found", "not_found_suara"),
        "error": ("error", "error_suara"),
        "disabled": ("disabled", "disabled"),
    }
    text_key, suara_key = key_map.get(result_status, ("not_intent", "not_intent"))
    text_tpl = templates.get(text_key, "")
    suara_tpl = templates.get(suara_key, text_tpl)

    if not text_tpl:
        return "", ""

    return text_tpl.format(app=name), suara_tpl.format(app=name)


def process_voice_command(text: str, karakter: str = "shiro", *, enabled: bool = True) -> LaunchResult:
    """
    Main entry: parse → resolve → launch → character callback payload.
    handled=False means caller should fall through to normal chat.
    """
    karakter = "sishin" if karakter == "sishin" else "shiro"

    if not enabled:
        return LaunchResult(handled=False, success=False, status="disabled", karakter=karakter, raw_text=text)

    intent = parse_launch_intent(text)
    if not intent:
        return LaunchResult(handled=False, success=False, status="not_intent", karakter=karakter, raw_text=text)

    target = resolve_app_target(intent.app_query)
    if not target:
        msg, suara = build_character_response("not_found", karakter, app_query=intent.app_query)
        return LaunchResult(
            handled=True,
            success=False,
            status="not_found",
            app_label=intent.app_query,
            message=msg,
            suara=suara,
            karakter=karakter,
            raw_text=text,
        )

    ok, err = launch_application(target)
    if ok:
        msg, suara = build_character_response("success", karakter, app_label=target.label)
        return LaunchResult(
            handled=True,
            success=True,
            status="success",
            app_label=target.label,
            app_id=target.app_id,
            message=msg,
            suara=suara,
            karakter=karakter,
            raw_text=text,
        )

    msg, suara = build_character_response("error", karakter, app_label=target.label)
    return LaunchResult(
        handled=True,
        success=False,
        status="error",
        app_label=target.label,
        app_id=target.app_id,
        message=msg + (f" ({err})" if err else ""),
        suara=suara,
        karakter=karakter,
        raw_text=text,
    )


def list_catalog() -> list[dict[str, Any]]:
    """Public catalog for UI / docs."""
    out = []
    for app_id, meta in sorted(WINDOWS_APPS.items(), key=lambda x: x[1].get("label", x[0])):
        out.append({
            "id": app_id,
            "label": meta.get("label", app_id),
            "aliases": meta.get("aliases", []),
            "installed": _resolve_executable(meta) is not None,
        })
    return out
