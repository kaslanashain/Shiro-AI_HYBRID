#!/usr/bin/env python3
"""Buat model Ollama offline shiro-ai & sishin-ai dari Modelfile proyek."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import config  # noqa: E402
from scripts.gguf_local import describe_gguf_for_user, resolve_gguf_from_line  # noqa: E402


def _ollama_bin() -> str:
    path = shutil.which("ollama")
    if not path:
        raise RuntimeError("Ollama tidak ditemukan di PATH. Install dari https://ollama.com")
    return path


def _registry_from_line() -> str:
    base = config.OLLAMA_MODEL or "qwen2.5:3b"
    return f"FROM {base}"


def _resolve_from_candidates() -> list[str]:
    """Urutan percobaan: GGUF lokal (jika ada) → registry Ollama."""
    force_registry = os.environ.get("OLLAMA_USE_LOCAL_GGUF", "").lower() in ("0", "false", "no")
    candidates: list[str] = []

    if not force_registry:
        gguf_line = resolve_gguf_from_line()
        if gguf_line:
            candidates.append(gguf_line)

    registry = _registry_from_line()
    if registry not in candidates:
        candidates.append(registry)

    return candidates


def _write_temp_modelfile(template_name: str, from_line: str) -> str:
    src = os.path.join(ROOT, "models", template_name)
    if not os.path.isfile(src):
        raise FileNotFoundError(f"Template tidak ditemukan: {src}")

    with open(src, encoding="utf-8") as f:
        lines = f.readlines()

    out_lines = []
    replaced = False
    for line in lines:
        if line.strip().startswith("FROM ") or line.strip().startswith("# FROM"):
            if not replaced:
                out_lines.append(from_line + "\n")
                replaced = True
            continue
        if line.startswith("# "):
            continue
        out_lines.append(line)

    if not replaced:
        out_lines.insert(0, from_line + "\n")

    fd, path = tempfile.mkstemp(suffix=".modelfile", prefix="shiro_")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)
    return path


def _create_model(name: str, template: str, from_line: str) -> bool:
    ollama = _ollama_bin()
    modelfile = _write_temp_modelfile(template, from_line)
    try:
        print(f"\n[BUILD] ollama create {name} ...")
        print(f"        {from_line}")
        proc = subprocess.run(
            [ollama, "create", name, "-f", modelfile],
            cwd=ROOT,
            timeout=900,
        )
        if proc.returncode != 0:
            print(f"[ERROR] Gagal membuat {name} (exit {proc.returncode})")
            return False
        print(f"[OK] Model {name} siap")
        return True
    finally:
        try:
            os.remove(modelfile)
        except OSError:
            pass


def _create_model_with_fallback(name: str, template: str, from_candidates: list[str]) -> bool:
    for from_line in from_candidates:
        if _create_model(name, template, from_line):
            return True
        if from_line.startswith('FROM "') or from_line.startswith("FROM ./"):
            print(f"[WARN] GGUF gagal untuk {name}, coba base berikutnya...")
    return False


def main() -> int:
    print("=" * 56)
    print("  Shiro AI — Setup Model Offline (Shiro & Sishin)")
    print("=" * 56)
    print(f"[INFO] {describe_gguf_for_user()}")

    from_candidates = _resolve_from_candidates()
    print(f"[INFO] Urutan base model: {len(from_candidates)} kandidat")

    ok_shiro = _create_model_with_fallback("shiro-ai", "Modelfile.shiro", from_candidates)
    ok_sishin = _create_model_with_fallback("sishin-ai", "Modelfile.sishin", from_candidates)

    if ok_shiro and ok_sishin:
        print("\n[SUKSES] Kedua model offline siap!")
        print("  Shiro  -> shiro-ai")
        print("  Sishin -> sishin-ai")
        print("\nJalankan desktop: .\\start_desktop.bat")
        return 0

    print("\n[GAGAL] Satu atau lebih model gagal dibuat. Pastikan Ollama berjalan.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
