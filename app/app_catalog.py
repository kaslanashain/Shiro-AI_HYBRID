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
_CACHE_TTL_SEC = 3600

_merged_cache: Optional[dict[str, dict[str, Any]]] = None
_merged_cache_at: float = 0.0


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


def _resolve_lnk(lnk_path: str) -> Optional[str]:
    if sys.platform != "win32" or not lnk_path.lower().endswith(".lnk"):
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
        logger.debug("LNK resolve failed for %s: %s", lnk_path, exc)
    return None


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
        ".zip", ".rar", ".7z", ".csv", ".md", ".json", ".py", ".html",
    }


def _scan_start_menu() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if sys.platform != "win32":
        return out

    roots = [
        _expand_path(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        _expand_path(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
        _expand_path(r"%USERPROFILE%\Desktop"),
    ]
    seen_targets: set[str] = set()

    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if not name.lower().endswith(".lnk"):
                    continue
                full = os.path.join(dirpath, name)
                target = _resolve_lnk(full)
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
            "%USERPROFILE%\\Desktop",
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

    for raw_root in roots:
        root = _expand_path(str(raw_root))
        if not os.path.isdir(root):
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
                full = os.path.join(dirpath, fn)
                if not os.path.isfile(full):
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
        _scan_start_menu(),
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
    global _merged_cache, _merged_cache_at
    _merged_cache = None
    _merged_cache_at = 0.0
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


def build_alias_index(registry: dict[str, dict]) -> dict[str, str]:
    index: dict[str, str] = {}
    for key, entry in registry.items():
        index[key.lower()] = key
        label = (entry.get("label") or key).lower()
        index[label] = key
        for alias in entry.get("aliases") or []:
            if alias:
                index[str(alias).lower()] = key
        path = entry.get("path")
        if path:
            base = os.path.basename(path)
            stem = os.path.splitext(base)[0].lower()
            if stem:
                index[stem] = key
            if base.lower():
                index[base.lower()] = key
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
