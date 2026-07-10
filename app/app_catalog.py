"""
App & file catalog for Shiro AI — built-in list + PC scan + user additions.

User additions:
  app/data/user_apps/custom_apps.json   — edit manually
  app/data/user_apps/tambah_di_sini/    — drop .lnk or .json when you install new software
  app/data/user_paths.json              — folders to index for files
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_BUILTIN_APPS = _DATA_DIR / "windows_apps.json"
_USER_APPS_DIR = _DATA_DIR / "user_apps"
_ADD_HERE_DIR = _USER_APPS_DIR / "tambah_di_sini"
_SHORTCUTS_DIR = _USER_APPS_DIR / "shortcuts"
_CUSTOM_APPS = _USER_APPS_DIR / "custom_apps.json"
_USER_PATHS = _DATA_DIR / "user_paths.json"
_CACHE_FILE = _USER_APPS_DIR / "_discovered_cache.json"

_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
_DETACHED_PROCESS = 0x00000008 if sys.platform == "win32" else 0
_CACHE_TTL_SEC = 3600
_LAUNCH_CACHE_TTL_SEC = 300

_merged_cache: Optional[dict[str, dict[str, Any]]] = None
_merged_cache_at: float = 0.0
_launch_registry_cache: Optional[dict[str, dict[str, Any]]] = None
_launch_registry_at: float = 0.0
_desktop_cache: Optional[dict[str, dict[str, Any]]] = None
_desktop_cache_at: float = 0.0
_DESKTOP_CACHE_TTL_SEC = 300


def _expand_path(path: str) -> str:
    return os.path.expanduser(os.path.expandvars(path or ""))


def _ensure_dirs() -> None:
    for d in (_USER_APPS_DIR, _ADD_HERE_DIR, _SHORTCUTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return default


def _save_json(path: Path, data: Any) -> None:
    _ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _slug_key(name: str, prefix: str = "") -> str:
    base = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    if not base:
        base = "item"
    return f"{prefix}{base}" if prefix else base


def _is_desktop_path(path: str) -> bool:
    """True if path is on user/public/OneDrive Desktop — never scan or touch shortcuts here."""
    p = os.path.normcase(os.path.abspath(_expand_path(path)))
    for env in (
        r"%USERPROFILE%\Desktop",
        r"%PUBLIC%\Desktop",
        r"%OneDrive%\Desktop",
        r"%OneDriveConsumer%\Desktop",
    ):
        d = os.path.normcase(_expand_path(env))
        if d and (p == d or p.startswith(d + os.sep)):
            return True
    return False


def _is_allowed_shortcut_path(lnk_path: str) -> bool:
    """Shortcuts in user_apps/ or Desktop (read-only launch via os.startfile)."""
    abs_lnk = os.path.normcase(os.path.abspath(_expand_path(lnk_path)))
    allowed_user = os.path.normcase(os.path.abspath(str(_USER_APPS_DIR)))
    if abs_lnk.startswith(allowed_user + os.sep) or abs_lnk.startswith(allowed_user):
        return True
    for desktop in _desktop_directories():
        desk = os.path.normcase(os.path.abspath(desktop))
        if abs_lnk.startswith(desk + os.sep) or abs_lnk == desk:
            return True
    return False


def _read_lnk_target(lnk_path: str) -> Optional[str]:
    """Read .lnk target path only — never writes or modifies the shortcut file."""
    if sys.platform != "win32" or not lnk_path.lower().endswith(".lnk"):
        return None
    if not os.path.isfile(lnk_path):
        return None
    try:
        escaped = lnk_path.replace("'", "''")
        cmd = f"(New-Object -ComObject WScript.Shell).CreateShortcut('{escaped}').TargetPath"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=_CREATE_NO_WINDOW,
        )
        target = (result.stdout or "").strip().strip('"')
        if target and os.path.exists(target):
            return target
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("LNK read failed for %s: %s", lnk_path, exc)
    return None


def _resolve_lnk(lnk_path: str) -> Optional[str]:
    if not _is_allowed_shortcut_path(lnk_path):
        logger.debug("Skip disallowed shortcut path: %s", lnk_path)
        return None
    return _read_lnk_target(lnk_path)


def _desktop_directories() -> list[str]:
    """All Desktop folder locations (local, public, OneDrive)."""
    seen: set[str] = set()
    dirs: list[str] = []
    for env in (
        r"%USERPROFILE%\Desktop",
        r"%PUBLIC%\Desktop",
        r"%OneDrive%\Desktop",
        r"%OneDriveConsumer%\Desktop",
    ):
        d = _expand_path(env)
        if not os.path.isdir(d):
            continue
        norm = os.path.normcase(os.path.abspath(d))
        if norm in seen:
            continue
        seen.add(norm)
        dirs.append(d)
    return dirs


def _entry_from_path(
    key: str,
    label: str,
    path: str,
    *,
    item_type: str = "app",
    aliases: Optional[list[str]] = None,
    source: str = "user",
) -> dict[str, Any]:
    return {
        "label": label,
        "type": item_type,
        "path": path,
        "aliases": aliases or [],
        "source": source,
        "key": key,
    }


def _load_user_json_files() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for folder in (_USER_APPS_DIR, _ADD_HERE_DIR, _SHORTCUTS_DIR):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.json")):
            if path.name.startswith("_"):
                continue
            data = _load_json(path, {})
            if not isinstance(data, dict):
                continue
            for key, entry in data.items():
                if isinstance(entry, dict) and (entry.get("path") or entry.get("exe")):
                    entry = dict(entry)
                    entry.setdefault("source", f"user:{path.name}")
                    out[key] = entry
    custom = _load_json(_CUSTOM_APPS, {})
    if isinstance(custom, dict):
        for key, entry in custom.items():
            if isinstance(entry, dict) and (entry.get("path") or entry.get("exe")):
                entry = dict(entry)
                entry.setdefault("source", "custom_apps.json")
                out[key] = entry
    return out


def _load_shortcuts_from_dirs() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for folder in (_ADD_HERE_DIR, _SHORTCUTS_DIR):
        if not folder.is_dir():
            continue
        for lnk in sorted(folder.rglob("*.lnk")):
            target = _resolve_lnk(str(lnk))
            if not target:
                continue
            label = lnk.stem
            key = _slug_key(label, prefix="lnk_")
            while key in out:
                key = key + "_2"
            item_type = "folder" if os.path.isdir(target) else "file" if _is_document(target) else "app"
            out[key] = _entry_from_path(key, label, target, item_type=item_type, source=str(folder.name))
    return out


def _is_document(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in {
        ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".mp4", ".wav",
        ".zip", ".rar", ".7z", ".csv", ".md", ".json", ".py", ".html", ".jar",
    }


def _scan_desktop_readonly(*, force_refresh: bool = False) -> dict[str, dict[str, Any]]:
    """
    Index Desktop items read-only — never copy, move, or modify shortcuts.
    Launch uses os.startfile(.lnk) or direct path; Desktop files stay in place.
    """
    global _desktop_cache, _desktop_cache_at
    now = time.time()
    if (
        not force_refresh
        and _desktop_cache is not None
        and (now - _desktop_cache_at) < _DESKTOP_CACHE_TTL_SEC
    ):
        return _desktop_cache

    out: dict[str, dict[str, Any]] = {}
    if sys.platform != "win32":
        _desktop_cache = out
        _desktop_cache_at = now
        return out

    seen_labels: set[str] = set()

    for desktop in _desktop_directories():
        try:
            names = os.listdir(desktop)
        except OSError as exc:
            logger.debug("Cannot list desktop %s: %s", desktop, exc)
            continue

        for name in names:
            full = os.path.join(desktop, name)
            if name.startswith("."):
                continue

            ext = Path(name).suffix.lower()
            label = Path(name).stem
            label_key = label.lower().strip()
            if not label_key or label_key in seen_labels:
                continue

            if ext == ".lnk":
                target = _read_lnk_target(full)
                key = _slug_key(label, prefix="desk_")
                while key in out:
                    key = key + "_2"
                entry = _entry_from_path(
                    key,
                    label,
                    target or full,
                    item_type="app",
                    aliases=[label_key, name.lower()],
                    source="desktop",
                )
                entry["shortcut"] = full
                if target:
                    entry["path"] = target
                else:
                    entry["use_startfile"] = True
                out[key] = entry
                seen_labels.add(label_key)
                continue

            if ext in (".exe", ".bat", ".cmd", ".msi", ".url"):
                key = _slug_key(label, prefix="desk_")
                while key in out:
                    key = key + "_2"
                out[key] = _entry_from_path(
                    key,
                    label,
                    full,
                    item_type="app",
                    aliases=[label_key, name.lower()],
                    source="desktop",
                )
                out[key]["use_startfile"] = ext in (".bat", ".cmd", ".url")
                seen_labels.add(label_key)
                continue

            if os.path.isdir(full):
                key = _slug_key(label, prefix="deskdir_")
                while key in out:
                    key = key + "_2"
                out[key] = _entry_from_path(
                    key,
                    label,
                    full,
                    item_type="folder",
                    aliases=[label_key, f"folder {label_key}"],
                    source="desktop",
                )
                seen_labels.add(label_key)
                continue

            if os.path.isfile(full) and _is_document(full):
                key = _slug_key(label, prefix="deskfile_")
                while key in out:
                    key = key + "_2"
                out[key] = _entry_from_path(
                    key,
                    name,
                    full,
                    item_type="file",
                    aliases=[label_key, name.lower(), f"file {label_key}"],
                    source="desktop",
                )
                seen_labels.add(label_key)

    _desktop_cache = out
    _desktop_cache_at = now
    logger.info("Desktop index (read-only): %d items", len(out))
    return out


def _scan_start_menu() -> dict[str, dict[str, Any]]:
    """
    Read Start Menu shortcuts only (NOT Desktop).
    Desktop shortcuts are never scanned — prevents shortcut removal/corruption.
    """
    out: dict[str, dict[str, Any]] = {}
    if sys.platform != "win32":
        return out

    roots = [
        _expand_path(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        _expand_path(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
    ]
    seen_targets: set[str] = set()

    for root in roots:
        if not os.path.isdir(root) or _is_desktop_path(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            if _is_desktop_path(dirpath):
                continue
            for name in filenames:
                if not name.lower().endswith(".lnk"):
                    continue
                full = os.path.join(dirpath, name)
                target = _read_lnk_target(full)
                if not target or target in seen_targets:
                    continue
                seen_targets.add(target)
                label = Path(name).stem
                key = _slug_key(label, prefix="sm_")
                while key in out:
                    key = key + "_2"
                item_type = "folder" if os.path.isdir(target) else "file" if _is_document(target) else "app"
                out[key] = _entry_from_path(
                    key,
                    label,
                    target,
                    item_type=item_type,
                    aliases=[label.lower()],
                    source="start_menu",
                )
    return out


def _load_user_paths_config() -> dict[str, Any]:
    default = {
        "scan_roots": [
            "%USERPROFILE%\\Documents",
            "%USERPROFILE%\\Downloads",
        ],
        "extra_folders": [],
        "max_files_per_root": 600,
        "max_depth": 4,
    }
    cfg = _load_json(_USER_PATHS, default)
    if not isinstance(cfg, dict):
        return default
    merged = dict(default)
    merged.update(cfg)
    return merged


def _index_files_and_folders() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    cfg = _load_user_paths_config()
    roots = list(cfg.get("scan_roots") or []) + list(cfg.get("extra_folders") or [])
    max_files = int(cfg.get("max_files_per_root") or 600)
    max_depth = int(cfg.get("max_depth") or 4)

    skip_ext = {".lnk", ".url", ".ini", ".desktop"}

    for raw_root in roots:
        root = _expand_path(str(raw_root))
        if not os.path.isdir(root) or _is_desktop_path(root):
            continue
        count = 0
        root_norm = os.path.normcase(root)
        for dirpath, dirnames, filenames in os.walk(root):
            depth = dirpath[len(root):].count(os.sep) if dirpath != root else 0
            if depth >= max_depth:
                dirnames[:] = []

            folder_name = os.path.basename(dirpath)
            if folder_name and depth > 0:
                fkey = _slug_key(folder_name, prefix="dir_")
                if fkey not in out:
                    out[fkey] = _entry_from_path(
                        fkey,
                        folder_name,
                        dirpath,
                        item_type="folder",
                        aliases=[folder_name.lower()],
                        source="scan",
                    )

            for fn in filenames:
                if count >= max_files:
                    break
                if Path(fn).suffix.lower() in skip_ext:
                    continue
                full = os.path.join(dirpath, fn)
                if not os.path.isfile(full) or _is_desktop_path(full):
                    continue
                count += 1
                stem = Path(fn).stem
                fkey = _slug_key(stem, prefix="file_")
                if fkey in out:
                    continue
                out[fkey] = _entry_from_path(
                    fkey,
                    fn,
                    full,
                    item_type="file",
                    aliases=[stem.lower(), fn.lower()],
                    source="scan",
                )

    return out


def get_launch_registry(*, force_refresh: bool = False) -> dict[str, dict[str, Any]]:
    """
    App registry for launching: built-in + user + registry + Desktop (read-only index).
  Desktop shortcuts are never moved or deleted — only opened via os.startfile.
    """
    global _launch_registry_cache, _launch_registry_at
    if force_refresh:
        _launch_registry_cache = None
        _launch_registry_at = 0.0
    now = time.time()
    if _launch_registry_cache is not None and (now - _launch_registry_at) < _LAUNCH_CACHE_TTL_SEC:
        return _launch_registry_cache

    merged: dict[str, dict[str, Any]] = {}
    builtin = _load_json(_BUILTIN_APPS, {})
    if isinstance(builtin, dict):
        for key, entry in builtin.items():
            if isinstance(entry, dict):
                e = dict(entry)
                e.setdefault("type", "app")
                e.setdefault("source", "builtin")
                merged[key] = e

    for source_map in (
        _load_user_json_files(),
        _load_shortcuts_from_dirs(),
        _discovered_from_registry(),
    ):
        for key, entry in source_map.items():
            if key not in merged:
                merged[key] = entry

    # Desktop last — adds desk_* entries; also fills builtin gaps (e.g. Cursor.lnk)
    desktop_items = _scan_desktop_readonly(force_refresh=force_refresh)
    label_to_builtin: dict[str, str] = {}
    for key, entry in merged.items():
        lbl = (entry.get("label") or key).lower()
        label_to_builtin[lbl] = key

    for dkey, dentry in desktop_items.items():
        merged[dkey] = dentry
        lbl = (dentry.get("label") or "").lower()
        if lbl and lbl in label_to_builtin:
            bkey = label_to_builtin[lbl]
            bent = merged.get(bkey, {})
            if not resolve_catalog_path(bent) and resolve_launch_path(dentry):
                merged[bkey] = {**bent, **dentry, "key": bkey, "source": "desktop+builtin"}

    _launch_registry_cache = merged
    _launch_registry_at = now
    logger.info("Launch registry loaded: %d apps (incl. desktop read-only)", len(merged))
    return merged


def _load_registry_paths() -> dict[str, str]:
    index: dict[str, str] = {}
    if sys.platform != "win32":
        return index
    try:
        import winreg
    except ImportError:
        return index

    subkeys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
    ]
    for hive, sub in subkeys:
        try:
            with winreg.OpenKey(hive, sub) as root:
                for i in range(winreg.QueryInfoKey(root)[0]):
                    try:
                        exe_name = winreg.EnumKey(root, i)
                        with winreg.OpenKey(root, exe_name) as app_key:
                            path, _ = winreg.QueryValueEx(app_key, "")
                        path = (path or "").strip().strip('"')
                        if path and os.path.isfile(path):
                            stem = exe_name.lower().replace(".exe", "")
                            index[stem] = path
                            index[exe_name.lower()] = path
                    except OSError:
                        continue
        except OSError:
            continue
    return index


def _discovered_from_registry() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for alias, path in _load_registry_paths().items():
        if alias.endswith(".exe") or len(alias) < 3:
            continue
        key = _slug_key(alias, prefix="reg_")
        if key in out:
            continue
        out[key] = _entry_from_path(
            key,
            alias.replace("_", " ").title(),
            path,
            item_type="app",
            aliases=[alias],
            source="registry",
        )
    return out


def scan_catalog(*, use_cache: bool = True) -> dict[str, dict[str, Any]]:
    """Full scan: built-in + user + Start Menu + files + registry."""
    _ensure_dirs()

    if use_cache and _CACHE_FILE.is_file():
        try:
            age = time.time() - _CACHE_FILE.stat().st_mtime
            if age < _CACHE_TTL_SEC:
                cached = _load_json(_CACHE_FILE, {})
                if isinstance(cached, dict) and cached.get("items"):
                    return cached["items"]
        except OSError:
            pass

    merged: dict[str, dict[str, Any]] = {}

    builtin = _load_json(_BUILTIN_APPS, {})
    if isinstance(builtin, dict):
        for key, entry in builtin.items():
            if isinstance(entry, dict):
                e = dict(entry)
                e.setdefault("type", "app")
                e.setdefault("source", "builtin")
                merged[key] = e

    for source_map in (
        _load_user_json_files(),
        _load_shortcuts_from_dirs(),
        _discovered_from_registry(),
        _scan_desktop_readonly(),
        _index_files_and_folders(),
    ):
        for key, entry in source_map.items():
            if key not in merged:
                merged[key] = entry

    _save_json(
        _CACHE_FILE,
        {
            "scanned_at": time.time(),
            "count": len(merged),
            "items": merged,
        },
    )
    logger.info("App catalog scanned: %d items", len(merged))
    return merged


def invalidate_catalog_cache() -> None:
    global _merged_cache, _merged_cache_at, _launch_registry_cache, _launch_registry_at
    global _desktop_cache, _desktop_cache_at
    _merged_cache = None
    _merged_cache_at = 0.0
    _launch_registry_cache = None
    _launch_registry_at = 0.0
    _desktop_cache = None
    _desktop_cache_at = 0.0
    try:
        if _CACHE_FILE.is_file():
            _CACHE_FILE.unlink()
    except OSError:
        pass


def get_merged_registry(*, force_rescan: bool = False) -> dict[str, dict[str, Any]]:
    global _merged_cache, _merged_cache_at
    if force_rescan:
        invalidate_catalog_cache()
    now = time.time()
    if _merged_cache is not None and (now - _merged_cache_at) < 120:
        return _merged_cache
    _merged_cache = scan_catalog(use_cache=not force_rescan)
    _merged_cache_at = now
    return _merged_cache


def rescan_catalog() -> dict[str, Any]:
    invalidate_catalog_cache()
    get_launch_registry(force_refresh=True)
    items = get_merged_registry(force_rescan=True)
    apps = sum(1 for e in items.values() if e.get("type", "app") == "app")
    files = sum(1 for e in items.values() if e.get("type") == "file")
    folders = sum(1 for e in items.values() if e.get("type") == "folder")
    return {
        "ok": True,
        "total": len(items),
        "apps": apps,
        "files": files,
        "folders": folders,
        "add_here": str(_ADD_HERE_DIR),
    }


def resolve_catalog_path(entry: dict[str, Any]) -> Optional[str]:
    """Resolve executable or file/folder path from a catalog entry."""
    shortcut = entry.get("shortcut")
    if shortcut:
        sp = _expand_path(str(shortcut))
        if os.path.isfile(sp):
            direct = entry.get("path")
            if direct:
                dp = _expand_path(direct)
                if os.path.exists(dp):
                    return dp
            return sp

    direct = entry.get("path")
    if direct:
        p = _expand_path(direct)
        if os.path.exists(p):
            return p

    if entry.get("use_startfile") and entry.get("exe", "").startswith("ms-"):
        return entry["exe"]

    for raw in entry.get("paths") or []:
        p = _expand_path(raw)
        if p and os.path.isfile(p):
            return p

    import glob as glob_mod

    for pattern in entry.get("glob_paths") or []:
        expanded = _expand_path(pattern)
        if not expanded:
            continue
        recursive = "**" in expanded
        matches = sorted(glob_mod.glob(expanded, recursive=recursive), reverse=True)
        for candidate in matches:
            if os.path.isfile(candidate):
                return candidate

    exe_name = entry.get("exe") or ""
    if exe_name:
        import shutil

        found = shutil.which(exe_name)
        if found and os.path.isfile(found):
            return found

    return None


def resolve_launch_path(entry: dict[str, Any]) -> Optional[str]:
    """Best launch target — resolved exe/file/folder or Desktop .lnk."""
    return resolve_catalog_path(entry)


def find_desktop_item(query: str) -> tuple[Optional[str], Optional[dict[str, Any]], float]:
    """Lookup on Desktop only (read-only index)."""
    registry = _scan_desktop_readonly()
    key, score = resolve_catalog_key(query, registry)
    if not key:
        return None, None, 0.0
    return key, registry.get(key), score


def build_alias_index(registry: dict[str, dict]) -> dict[str, str]:
    index: dict[str, str] = {}

    def _set(alias: str, key: str) -> None:
        al = (alias or "").lower()
        if not al:
            return
        if key.startswith("desk_") and al in index:
            return
        index[al] = key

    for key, entry in registry.items():
        _set(key, key)
        _set(entry.get("label") or key, key)
        for alias in entry.get("aliases") or []:
            _set(str(alias), key)
        path = entry.get("path")
        if path:
            base = os.path.basename(path)
            stem = os.path.splitext(base)[0]
            _set(stem, key)
            _set(base, key)
        shortcut = entry.get("shortcut")
        if shortcut:
            stem = os.path.splitext(os.path.basename(str(shortcut)))[0]
            _set(stem, key)
    return index


def resolve_catalog_key(app_query: str, registry: Optional[dict] = None) -> tuple[Optional[str], float]:
    registry = registry or get_merged_registry()
    if not registry:
        return None, 0.0

    query = app_query.lower().strip()
    query = re.sub(r"^(?:file|berkas|dokumen|folder|map|direktori)\s+", "", query, flags=re.IGNORECASE)

    alias_index = build_alias_index(registry)
    if query in alias_index:
        return alias_index[query], 1.0

    for alias, key in sorted(alias_index.items(), key=lambda x: -len(x[0])):
        if len(alias) < 2:
            continue
        if alias in query or query in alias:
            return key, 0.92

    keys = list(alias_index.keys())
    matches = get_close_matches(query, keys, n=1, cutoff=0.58)
    if matches:
        return alias_index[matches[0]], 0.72

    return None, 0.0


def get_add_here_path() -> str:
    _ensure_dirs()
    return str(_ADD_HERE_DIR)


def list_catalog_items(limit: int = 500) -> list[dict[str, Any]]:
    registry = get_merged_registry()
    out = []
    for key, entry in registry.items():
        path = resolve_catalog_path(entry)
        out.append(
            {
                "key": key,
                "label": entry.get("label") or key.title(),
                "type": entry.get("type", "app"),
                "installed": bool(path),
                "source": entry.get("source", ""),
            }
        )
    out.sort(key=lambda x: (x["type"], x["label"].lower()))
    return out[:limit]
