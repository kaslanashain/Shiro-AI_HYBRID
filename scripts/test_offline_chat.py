"""Uji mode offline — respons & naturalitas Shiro/Sishin."""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Paksa offline
os.environ["GROQ_API_KEY"] = ""

import app.chat as chat  # noqa: E402

chat.GROQ_API_KEY = ""
chat.is_internet_available = lambda: False

CASES = [
    ("shiro", "Sayang, aku kangen banget hari ini"),
    ("shiro", "konnichiwa Shiro-chan, genki?"),
    ("sishin", "Sishin! ayo main game yuk!"),
    ("sishin", "menurutmu onee-chan Shiro manja nggak?"),
]


def main():
    print("=" * 56)
    print("  UJI OFFLINE — jawab_shiro (Groq dimatikan)")
    print("  Tip: pertama kali ~1-3 menit jika model belum di RAM")
    print("=" * 56)

    # Warmup dulu
    from app.llm_offline import warmup_offline_model
    print("\n[WARMUP] Memuat model ke RAM...")
    t_w = time.time()
    warmup_offline_model("shiro")
    print(f"[WARMUP] Selesai ({time.time() - t_w:.1f}s)\n")

    times = []
    for karakter, pesan in CASES:
        t0 = time.time()
        try:
            result, status = chat.jawab_shiro(
                pesan, preferred_karakter=karakter, force_preferred=True
            )
            elapsed = time.time() - t0
            times.append(elapsed)
            text = result.get("text", "")
            suara = result.get("suara", "")
            print(f"\n--- {karakter.upper()} ({elapsed:.1f}s) ---")
            print(f"USER  : {pesan}")
            print(f"LAYAR : {text}")
            print(f"SUARA : {suara}")
            print(f"Afeksi: {status.get('affection')}")
        except Exception as exc:
            print(f"\nERROR {karakter}: {exc}")

    if times:
        print("\n" + "=" * 56)
        print(f"Rata-rata respons: {sum(times)/len(times):.1f}s")
        print(f"Tercepat: {min(times):.1f}s | Terlambat: {max(times):.1f}s")
        if times[0] > 30:
            print("Catatan: respons pertama biasanya lambat (model loading).")


if __name__ == "__main__":
    main()
