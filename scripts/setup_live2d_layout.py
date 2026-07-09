"""Atur ulang folder Live2D: sample Haru/Hiyori + custom upload."""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE2D = os.path.join(ROOT, "static", "live2d")
SISHIN = os.path.join(LIVE2D, "sishin")
CUSTOM_SISHIN = os.path.join(LIVE2D, "custom", "sishin")
CUSTOM_SHIRO = os.path.join(LIVE2D, "custom", "shiro")
SAMPLES_HIYORI = os.path.join(LIVE2D, "samples", "hiyori")
ARCHIVE_HIYORI = os.path.join(LIVE2D, "_archive", "sishin_hiyori_sample")

VERSI_BARU_PREFIX = "Sishin_l2d_versi_baru"


def _copy_tree(src, dst):
    if os.path.isdir(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    elif os.path.isfile(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def _move_versi_baru_to_custom():
    os.makedirs(CUSTOM_SISHIN, exist_ok=True)
    for name in os.listdir(SISHIN):
        if name.startswith(VERSI_BARU_PREFIX):
            src = os.path.join(SISHIN, name)
            dst = os.path.join(CUSTOM_SISHIN, name)
            if os.path.isdir(src):
                _copy_tree(src, dst)
                shutil.rmtree(src)
            else:
                shutil.copy2(src, dst)
                os.remove(src)
            print(f"[CUSTOM] {name} -> custom/sishin/")


def _restore_hiyori_samples():
    if not os.path.isdir(ARCHIVE_HIYORI):
        print("[SKIP] Arsip Hiyori tidak ditemukan")
        return
    os.makedirs(SAMPLES_HIYORI, exist_ok=True)
    for name in os.listdir(ARCHIVE_HIYORI):
        src = os.path.join(ARCHIVE_HIYORI, name)
        dst = os.path.join(SAMPLES_HIYORI, name)
        if os.path.exists(dst):
            continue
        _copy_tree(src, dst)
        print(f"[SAMPLE] Hiyori: {name}")


def _ensure_custom_dirs():
    for path in (CUSTOM_SHIRO, CUSTOM_SISHIN):
        os.makedirs(path, exist_ok=True)
        os.makedirs(os.path.join(path, "motions"), exist_ok=True)


def main():
    _ensure_custom_dirs()
    _move_versi_baru_to_custom()
    _restore_hiyori_samples()
    print("[OK] Layout Live2D siap (Shiro=Haru, Sishin=Hiyori, custom=custom/)")


if __name__ == "__main__":
    main()
