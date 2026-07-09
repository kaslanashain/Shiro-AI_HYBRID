"""Wire motion files dari motions_sishin/ ke Sishin_l2d_versi_baru.model3.json."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SISHIN = os.path.join(ROOT, "static", "live2d", "sishin")
MODEL = os.path.join(SISHIN, "Sishin_l2d_versi_baru.model3.json")
MOTIONS_DIR = os.path.join(SISHIN, "motions_sishin")


def main():
    if not os.path.isfile(MODEL):
        print("[SKIP] Model tidak ditemukan:", MODEL)
        return

    with open(MODEL, encoding="utf-8") as f:
        data = json.load(f)

    refs = data.setdefault("FileReferences", {})
    motions = {}

    if os.path.isdir(MOTIONS_DIR):
        files = sorted(f for f in os.listdir(MOTIONS_DIR) if f.endswith(".motion3.json"))
        if files:
            idle = []
            tap = []
            for fname in files:
                entry = {
                    "File": f"motions_sishin/{fname}",
                    "FadeInTime": 0.5,
                    "FadeOutTime": 0.5,
                }
                lower = fname.lower()
                if "idle" in lower or "breath" in lower:
                    idle.append(entry)
                else:
                    tap.append(entry)
            if idle:
                motions["Idle"] = idle
            if tap:
                motions["TapBody"] = tap
            if not idle and tap:
                motions["Idle"] = tap[:1]

    if motions:
        refs["Motions"] = motions
        print(f"[OK] {sum(len(v) for v in motions.values())} gerakan dipasang")
    else:
        refs.pop("Motions", None)
        print("[INFO] Belum ada file .motion3.json di motions_sishin/ — pakai idle procedural")

    with open(MODEL, "w", encoding="utf-8") as f:
        json.dump(data, f, indent="\t", ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
