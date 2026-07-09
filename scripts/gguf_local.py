"""Status & path GGUF lokal untuk model offline Ollama."""
from __future__ import annotations

import os

from app.config import BASE_DIR, OLLAMA_GGUF_PATH

GGUF_PART1 = os.path.join(BASE_DIR, "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf")
GGUF_PART2 = os.path.join(BASE_DIR, "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf")

# Part2 split Q4 biasanya > 500 MB jika unduhan lengkap
MIN_PART2_BYTES = 500_000_000


def _file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def gguf_status() -> dict:
    """Ringkasan file GGUF di folder proyek."""
    custom = OLLAMA_GGUF_PATH if OLLAMA_GGUF_PATH and os.path.isabs(OLLAMA_GGUF_PATH) else ""
    if not custom and OLLAMA_GGUF_PATH:
        custom = os.path.join(BASE_DIR, OLLAMA_GGUF_PATH)

    part1_ok = os.path.isfile(GGUF_PART1)
    part2_ok = os.path.isfile(GGUF_PART2)
    part2_size = _file_size(GGUF_PART2) if part2_ok else 0
    split_complete = part1_ok and part2_ok and part2_size >= MIN_PART2_BYTES

    single_path = None
    if custom and os.path.isfile(custom) and "00001-of-" not in os.path.basename(custom):
        single_path = custom
    elif part1_ok and not part2_ok and "00001-of-" not in os.path.basename(GGUF_PART1):
        single_path = GGUF_PART1

    return {
        "part1": GGUF_PART1,
        "part2": GGUF_PART2,
        "part1_ok": part1_ok,
        "part2_ok": part2_ok,
        "part2_size_mb": round(part2_size / (1024 * 1024), 1),
        "split_complete": split_complete,
        "single_gguf": single_path,
        "custom_path": custom if custom and os.path.isfile(custom) else None,
    }


def resolve_gguf_from_line() -> str | None:
    """
    Return baris FROM untuk Modelfile jika GGUF siap dipakai Ollama.
    Prioritas: file tunggal > custom path > split shard (jika lengkap).
    """
    st = gguf_status()

    if st["single_gguf"]:
        return f'FROM "{os.path.abspath(st["single_gguf"])}"'

    if st["custom_path"] and "00001-of-" not in os.path.basename(st["custom_path"]):
        return f'FROM "{os.path.abspath(st["custom_path"])}"'

    if st["split_complete"]:
        # Path relatif dari ROOT — lebih stabil di Windows untuk Ollama
        rel = os.path.relpath(GGUF_PART1, BASE_DIR).replace("\\", "/")
        return f"FROM ./{rel}"

    return None


def describe_gguf_for_user() -> str:
    st = gguf_status()
    if st["single_gguf"]:
        return f"GGUF tunggal ditemukan: {st['single_gguf']}"
    if st["split_complete"]:
        return (
            f"GGUF split ditemukan (part1 + part2 {st['part2_size_mb']} MB). "
            "Akan dicoba untuk Ollama; jika gagal, fallback ke qwen2.5:3b registry."
        )
    if st["part1_ok"] and not st["part2_ok"]:
        return "GGUF part1 ada tapi part2 hilang — jalankan unduh_qwen.py untuk melengkapi."
    if st["part1_ok"] and st["part2_ok"] and not st["split_complete"]:
        return f"GGUF part2 terlalu kecil ({st['part2_size_mb']} MB) — unduhan mungkin belum lengkap."
    return "Tidak ada GGUF lokal — memakai model Ollama registry (qwen2.5:3b)."
