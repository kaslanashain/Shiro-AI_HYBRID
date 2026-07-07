"""
Shiro AI — Desktop pet launcher (Windows).

- Frameless always-on-top companion window (/desktop)
- System tray: show/hide, open full app, autostart toggle, quit
- Auto-starts Flask server if not running

Usage:
    python desktop_launcher.py
    pythonw desktop_launcher.py   (no console)

Requires: pip install pywebview pystray pillow
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
PORT = int(os.environ.get("FLASK_PORT", "5000"))
BASE_URL = f"http://{HOST}:{PORT}"
DESKTOP_URL = f"{BASE_URL}/desktop"
APP_URL = f"{BASE_URL}/"


class AppState:
    window = None
    server_proc: subprocess.Popen | None = None
    started_server = False
    tray_icon = None
    shutting_down = False


def _server_up() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/status", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _start_server_subprocess() -> subprocess.Popen | None:
    py = sys.executable
    env = os.environ.copy()
    env.setdefault("FLASK_HOST", HOST)
    env.setdefault("FLASK_PORT", str(PORT))
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        return subprocess.Popen(
            [py, "main.py"],
            cwd=ROOT,
            env=env,
            creationflags=flags,
        )
    except Exception as exc:
        print(f"[Desktop] Gagal start server: {exc}")
        return None


def _wait_for_server(timeout: float = 45.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _server_up():
            return True
        time.sleep(0.5)
    return False


def _tray_image():
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([6, 6, 58, 58], fill=(255, 107, 138, 255))
    draw.ellipse([22, 20, 30, 28], fill=(255, 255, 255, 230))
    draw.ellipse([34, 20, 42, 28], fill=(255, 255, 255, 230))
    draw.arc([20, 32, 44, 46], start=10, end=170, fill=(255, 255, 255, 220), width=2)
    return img


def _show_window():
    if AppState.window:
        try:
            AppState.window.show()
            AppState.window.restore()
        except Exception:
            pass


def _hide_window():
    if AppState.window:
        try:
            AppState.window.hide()
        except Exception:
            pass


def _open_full_app():
    webbrowser.open(APP_URL)


def _autostart_checked(_item) -> bool:
    try:
        from scripts.desktop_autostart import is_installed
        return is_installed()
    except Exception:
        return False


def _toggle_autostart(icon, _item):
    try:
        from scripts import desktop_autostart as autostart
        if autostart.is_installed():
            autostart.uninstall()
        else:
            autostart.install()
    except Exception as exc:
        print(f"[Desktop] Autostart error: {exc}")


def _quit_app(icon=None, _item=None):
    if AppState.shutting_down:
        return
    AppState.shutting_down = True
    if AppState.tray_icon:
        try:
            AppState.tray_icon.stop()
        except Exception:
            pass
    import webview
    try:
        webview.destroy_window()
    except Exception:
        pass
    if AppState.server_proc and AppState.server_proc.poll() is None and AppState.started_server:
        AppState.server_proc.terminate()
    os._exit(0)


def _start_tray():
    import pystray

    menu = pystray.Menu(
        pystray.MenuItem("Tampilkan Shiro", lambda *_: _show_window(), default=True),
        pystray.MenuItem("Sembunyikan", lambda *_: _hide_window()),
        pystray.MenuItem("Buka app lengkap", lambda *_: _open_full_app()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Jalankan saat Windows nyala",
            _toggle_autostart,
            checked=_autostart_checked,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Keluar", _quit_app),
    )
    AppState.tray_icon = pystray.Icon(
        "shiro_ai_desktop",
        _tray_image(),
        "Shiro AI Desktop",
        menu,
    )
    AppState.tray_icon.run()


class DesktopApi:
    """Exposed to JS via pywebview.api"""

    def hide_window(self):
        _hide_window()

    def show_window(self):
        _show_window()

    def quit_app(self):
        _quit_app()


def main() -> int:
    try:
        import webview  # noqa: F401
    except ImportError:
        print("pywebview belum terpasang. Jalankan: pip install pywebview pystray pillow")
        return 1

    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        print("pystray/pillow belum terpasang. Jalankan: pip install pystray pillow")
        return 1

    if not _server_up():
        print("[Desktop] Memulai server Shiro AI...")
        AppState.server_proc = _start_server_subprocess()
        AppState.started_server = True
        if not _wait_for_server():
            print("[Desktop] Server tidak merespons. Coba jalankan main.py manual.")
            if AppState.server_proc:
                AppState.server_proc.terminate()
            return 1

    threading.Thread(target=_start_tray, daemon=True).start()
    time.sleep(0.3)

    api = DesktopApi()
    AppState.window = webview.create_window(
        "Shiro AI Desktop",
        DESKTOP_URL,
        width=320,
        height=460,
        resizable=True,
        frameless=True,
        easy_drag=True,
        on_top=True,
        js_api=api,
    )

    try:
        webview.start()
    except KeyboardInterrupt:
        pass
    finally:
        if (
            AppState.server_proc
            and AppState.server_proc.poll() is None
            and AppState.started_server
        ):
            AppState.server_proc.terminate()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
