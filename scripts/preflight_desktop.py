#!/usr/bin/env python3
"""Preflight sebelum start_desktop.bat — deps, Ollama, model offline."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _pip_install(packages: list[str]) -> None:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", *packages],
        cwd=ROOT,
        check=False,
    )


def _ensure_desktop_deps() -> bool:
    missing = []
    for mod, pkg in (
        ("webview", "pywebview"),
        ("pystray", "pystray"),
        ("PIL", "pillow"),
    ):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[preflight] Menginstal: {', '.join(missing)}")
        _pip_install(missing)
    return True


def _ollama_running() -> bool:
    if not shutil.which("ollama"):
        print("[preflight] Ollama tidak ada di PATH — install dari https://ollama.com")
        return False
    try:
        from app.llm_offline import check_ollama_models
        status = check_ollama_models()
        if status.get("error"):
            print(f"[preflight] Ollama tidak merespons: {status['error']}")
            return False
        return True
    except Exception as exc:
        print(f"[preflight] Cek Ollama gagal: {exc}")
        return False


def _ensure_offline_models() -> None:
    try:
        from app.llm_offline import check_ollama_models
        status = check_ollama_models()
    except Exception as exc:
        print(f"[preflight] Tidak bisa cek model: {exc}")
        return

    if status.get("shiro") and status.get("sishin"):
        print("[preflight] Model offline OK: shiro-ai, sishin-ai")
        return

    print("[preflight] Model offline belum lengkap — menjalankan setup...")
    script = os.path.join(ROOT, "scripts", "setup_ollama_models.py")
    proc = subprocess.run([sys.executable, script], cwd=ROOT)
    if proc.returncode == 0:
        print("[preflight] Setup model offline selesai")
    else:
        print("[preflight] Setup model gagal — chat offline mungkin terbatas")


def _report_gguf() -> None:
    try:
        from scripts.gguf_local import describe_gguf_for_user
        print(f"[preflight] {describe_gguf_for_user()}")
    except Exception as exc:
        print(f"[preflight] GGUF: {exc}")


def main() -> int:
    os.chdir(ROOT)
    print("[preflight] Shiro AI Desktop — memeriksa sistem...")

    if not _ensure_desktop_deps():
        return 1

    _report_gguf()
    _ollama_running()
    _ensure_offline_models()

    print("[preflight] Siap — meluncurkan desktop companion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
