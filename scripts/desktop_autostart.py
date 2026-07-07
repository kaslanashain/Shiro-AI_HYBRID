"""Windows autostart helper for Shiro AI Desktop companion."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTOSTART_NAME = "Shiro_AI_Desktop.bat"


def startup_dir() -> Path:
    appdata = os.environ.get("APPDATA", "")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def autostart_path() -> Path:
    return startup_dir() / AUTOSTART_NAME


def _pythonw() -> str:
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    if pyw.is_file():
        return str(pyw)
    return str(exe)


def is_installed() -> bool:
    return autostart_path().is_file()


def install() -> Path:
    launcher = ROOT / "desktop_launcher.py"
    bat = (
        "@echo off\n"
        f'cd /d "{ROOT}"\n'
        f'start "" "{_pythonw()}" "{launcher}"\n'
    )
    path = autostart_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bat, encoding="utf-8")
    return path


def uninstall() -> bool:
    path = autostart_path()
    if path.is_file():
        path.unlink()
        return True
    return False


if __name__ == "__main__":
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    if cmd == "install":
        p = install()
        print(f"Autostart installed: {p}")
    elif cmd == "uninstall":
        print("Removed." if uninstall() else "Not installed.")
    else:
        print("installed" if is_installed() else "not_installed")
