"""Pasang model Live2D custom dari folder upload ke wardrobe."""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM = os.path.join(ROOT, "static", "live2d", "custom")

PREFERRED_NAMES = {
    "shiro": "Shiro_l2d.model3.json",
    "sishin": "Sishin_l2d.model3.json",
}


def find_model(char):
    folder = os.path.join(CUSTOM, char)
    if not os.path.isdir(folder):
        return None
    preferred = os.path.join(folder, PREFERRED_NAMES[char])
    if os.path.isfile(preferred):
        return preferred
    for name in sorted(os.listdir(folder)):
        if name.endswith(".model3.json"):
            return os.path.join(folder, name)
    return None


def wire_motions(model_path):
    folder = os.path.dirname(model_path)
    motions_dir = os.path.join(folder, "motions")
    if not os.path.isdir(motions_dir):
        return

    with open(model_path, encoding="utf-8") as f:
        data = json.load(f)

    refs = data.setdefault("FileReferences", {})
    motions = {}
    files = sorted(f for f in os.listdir(motions_dir) if f.endswith(".motion3.json"))
    if not files:
        return

    idle, tap = [], []
    for fname in files:
        entry = {"File": f"motions/{fname}", "FadeInTime": 0.5, "FadeOutTime": 0.5}
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

    refs["Motions"] = motions
    with open(model_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent="\t", ensure_ascii=False)
        f.write("\n")
    print(f"[OK] {len(files)} gerakan dipasang")


def main():
    for char in ("shiro", "sishin"):
        model = find_model(char)
        if not model:
            print(f"[SKIP] {char}: belum ada .model3.json di custom/{char}/")
            continue
        print(f"[OK] {char}: {os.path.basename(model)}")
        wire_motions(model)


if __name__ == "__main__":
    main()
