"""Bandingkan kecepatan & kualitas offline: qwen2.5:3b vs qwen2.5:7b (+ Groq opsional)."""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["GROQ_API_KEY"] = ""  # paksa offline untuk Ollama

import app.chat as chat  # noqa: E402
from app.llm_offline import call_ollama_offline, warmup_offline_model  # noqa: E402

chat.GROQ_API_KEY = ""
chat.is_internet_available = lambda: False

MODELS = ["qwen2.5:3b", "qwen2.5:7b"]

PROMPTS = [
    ("shiro", "Sayang, aku kangen banget hari ini"),
    ("shiro", "konnichiwa Shiro-chan, genki?"),
    ("sishin", "Sishin! ayo main game yuk!"),
    ("sishin", "menurutmu onee-chan Shiro manja nggak?"),
]


def _call_with_model(model: str, karakter: str, pesan: str) -> tuple[dict, float]:
    ctx = chat._prepare_chat(pesan, preferred_karakter=karakter, force_preferred=True)
    t0 = time.time()
    # Override model langsung (shared offline, persona dari system prompt)
    import ollama
    from app import config

    payload = __import__("app.llm_offline", fromlist=["enrich_offline_messages"]).enrich_offline_messages(
        ctx["messages"], karakter
    )
    opts = dict(config.OLLAMA_OFFLINE_OPTIONS)
    resp = ollama.Client(host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).chat(
        model=model,
        messages=payload,
        options=opts,
        keep_alive=config.OLLAMA_KEEP_ALIVE,
    )
    elapsed = time.time() - t0
    raw = resp["message"]["content"]
    result = chat._parse_model_response(raw, ctx["konteks"], karakter)
    return result, elapsed


def _try_groq_baseline() -> list[dict]:
    """Satu putaran Groq online sebagai pembanding (jika API key ada)."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return []

    chat.GROQ_API_KEY = key
    chat.groq_client = None
    try:
        from groq import Groq
        chat.groq_client = Groq(api_key=key)
        chat.is_internet_available = lambda: True
    except Exception:
        return []

    rows = []
    for karakter, pesan in PROMPTS:
        t0 = time.time()
        try:
            result, _ = chat.jawab_shiro(pesan, preferred_karakter=karakter, force_preferred=True)
            rows.append({
                "model": "Groq online",
                "karakter": karakter,
                "pesan": pesan,
                "layar": result.get("text", ""),
                "suara": result.get("suara", ""),
                "detik": round(time.time() - t0, 1),
            })
        except Exception as exc:
            rows.append({"model": "Groq online", "karakter": karakter, "pesan": pesan, "error": str(exc)})
    chat.GROQ_API_KEY = ""
    chat.is_internet_available = lambda: False
    return rows


def main():
    print("=" * 70)
    print("  BANDINGKAN OFFLINE: qwen2.5:3b vs qwen2.5:7b")
    print("=" * 70)

    all_rows: list[dict] = []

    for model in MODELS:
        print(f"\n{'#' * 70}")
        print(f"  MODEL: {model}")
        print(f"{'#' * 70}")
        print(f"[WARMUP] {model} ...")
        tw = time.time()
        try:
            import ollama
            from app import config
            ollama.Client().chat(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                options={"num_predict": 1, "num_ctx": 512},
                keep_alive=config.OLLAMA_KEEP_ALIVE,
            )
            print(f"[WARMUP] selesai ({time.time() - tw:.1f}s)")
        except Exception as exc:
            print(f"[WARMUP] gagal: {exc}")
            continue

        for karakter, pesan in PROMPTS:
            try:
                result, elapsed = _call_with_model(model, karakter, pesan)
                row = {
                    "model": model,
                    "karakter": karakter,
                    "pesan": pesan,
                    "layar": result.get("text", ""),
                    "suara": result.get("suara", ""),
                    "detik": round(elapsed, 1),
                }
                all_rows.append(row)
                print(f"\n--- {karakter.upper()} ({elapsed:.1f}s) ---")
                print(f"USER  : {pesan}")
                print(f"LAYAR : {row['layar']}")
            except Exception as exc:
                print(f"\nERROR {model} {karakter}: {exc}")
                all_rows.append({"model": model, "karakter": karakter, "pesan": pesan, "error": str(exc)})

    groq_rows = _try_groq_baseline()
    if groq_rows:
        print(f"\n{'#' * 70}")
        print("  BASELINE: Groq online")
        print(f"{'#' * 70}")
        for row in groq_rows:
            if "error" in row:
                print(f"ERROR: {row['error']}")
            else:
                print(f"\n--- {row['karakter'].upper()} ({row['detik']}s) ---")
                print(f"USER  : {row['pesan']}")
                print(f"LAYAR : {row['layar']}")

    # Ringkasan
    print("\n" + "=" * 70)
    print("  RINGKASAN WAKTU (detik)")
    print("=" * 70)
    for model in MODELS + (["Groq online"] if groq_rows else []):
        times = [r["detik"] for r in all_rows + groq_rows if r.get("model") == model and "detik" in r]
        if times:
            print(f"  {model:16} avg={sum(times)/len(times):.1f}s  min={min(times):.1f}s  max={max(times):.1f}s")

    # Simpan laporan
    out = os.path.join(ROOT, "tmp", "compare_offline_models.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for row in all_rows + groq_rows:
            f.write(f"\n[{row.get('model')}] {row.get('karakter')} ({row.get('detik', '?')}s)\n")
            f.write(f"USER: {row.get('pesan')}\n")
            f.write(f"LAYAR: {row.get('layar', row.get('error', ''))}\n")
            f.write("-" * 50 + "\n")
    print(f"\nLaporan lengkap: {out}")


if __name__ == "__main__":
    main()
