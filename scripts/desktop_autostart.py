"""Windows autostart helper for Shiro AI Desktop companion."""
from __future__ import annotations

import json
import os
import sys
import winreg
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTOSTART_NAME = "Shiro_AI_Desktop.bat"
REGISTRY_NAME = "Shiro AI Desktop"
SETTINGS_PATH = ROOT / "app" / "data" / "desktop_settings.json"
LOGIN_DELAY_SEC = 15


def startup_dir() -> Path:
    appdata = os.environ.get("APPDATA", "")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def autostart_path() -> Path:
    return startup_dir() / AUTOSTART_NAME


def _load_settings() -> dict:
    try:
        if SETTINGS_PATH.is_file():
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_settings(data: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def is_user_enabled() -> bool:
    """Default True — jalankan otomatis kecuali user matikan lewat tray."""
    return bool(_load_settings().get("autostart", True))


def set_user_enabled(enabled: bool) -> None:
    data = _load_settings()
    data["autostart"] = bool(enabled)
    _save_settings(data)


def _pythonw() -> str:
    venv_pyw = ROOT / "venv" / "Scripts" / "pythonw.exe"
    if venv_pyw.is_file():
        return str(venv_pyw)
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    if pyw.is_file():
        return str(pyw)
    return str(exe)


def _autostart_bat_content() -> str:
    pyw = _pythonw()
    launcher = ROOT / "desktop_launcher.py"
    return (
        "@echo off\n"
        "rem Shiro AI — jalankan otomatis saat Windows login / nyalakan laptop\n"
        f'cd /d "{ROOT}"\n'
        f"timeout /t {LOGIN_DELAY_SEC} /nobreak >nul\n"
        f'if exist "venv\\Scripts\\pythonw.exe" (\n'
        f'  "venv\\Scripts\\pythonw.exe" "{launcher}"\n'
        f") else (\n"
        f'  "{pyw}" "{launcher}"\n'
        f")\n"
    )


def _registry_run_key() -> str:
    return str(autostart_path())


def _registry_installed() -> bool:
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        ) as key:
            winreg.QueryValueEx(key, REGISTRY_NAME)
            return True
    except OSError:
        return False


def _install_registry() -> None:
    if sys.platform != "win32":
        return
    bat = _registry_run_key()
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, REGISTRY_NAME, 0, winreg.REG_SZ, bat)


def _uninstall_registry() -> None:
    if sys.platform != "win32":
        return
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, REGISTRY_NAME)
    except OSError:
        pass


def is_installed() -> bool:
    return autostart_path().is_file() or _registry_installed()


def install() -> Path:
    bat_text = _autostart_bat_content()
    path = autostart_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bat_text, encoding="utf-8")
    _install_registry()
    set_user_enabled(True)
    return path


def uninstall() -> bool:
    removed = False
    path = autostart_path()
    if path.is_file():
        path.unlink()
        removed = True
    if _registry_installed():
        _uninstall_registry()
        removed = True
    set_user_enabled(False)
    return removed


def ensure_autostart() -> None:
    """Pasang autostart jika user belum mematikan lewat menu tray."""
    if sys.platform != "win32":
        return
    if not is_user_enabled():
        return
    if not is_installed():
        path = install()
        print(f"[Desktop] Autostart Windows dipasang: {path}")


if __name__ == "__main__":
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    if cmd == "install":
        p = install()
        print(f"Autostart installed: {p}")
        print(f"Registry Run: HKCU\\...\\Run\\{REGISTRY_NAME}")
    elif cmd == "uninstall":
        print("Removed." if uninstall() else "Not installed.")
    elif cmd == "ensure":
        ensure_autostart()
        print("installed" if is_installed() else "not_installed")
    else:
        print("installed" if is_installed() else "not_installed")
        print(f"user_enabled={is_user_enabled()}")
