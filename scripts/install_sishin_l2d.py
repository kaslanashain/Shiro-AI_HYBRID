"""Pasang Sishin Live2D versi baru ke static/live2d/sishin/."""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SISHIN = os.path.join(ROOT, "static", "live2d", "sishin")
CUSTOM = os.path.join(ROOT, "static", "live2d", "sishin_custom")
ARCHIVE_OLD = os.path.join(ROOT, "static", "live2d", "_archive", "sishin_l2d_lama")
ARCHIVE_CUSTOM = os.path.join(ROOT, "static", "live2d", "_archive", "sishin_custom_removed")

VERSI_BARU_FILES = [
    "Sishin_l2d_versi_baru.model3.json",
    "Sishin_l2d_versi_baru.moc3",
    "Sishin_l2d_versi_baru.cdi3.json",
    "Sishin_l2d_versi_baru.2048",
]

OLD_SISHIN_L2D = [
    "Sishin_l2d.model3.json",
    "Sishin_l2d.moc3",
    "Sishin_l2d.cdi3.json",
    "Sishin_l2d.cmo3",
    "Sishin_l2d.2048",
]


def _copy_tree(src, dst):
    if os.path.isdir(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    elif os.path.isfile(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def main():
    os.makedirs(SISHIN, exist_ok=True)
    os.makedirs(ARCHIVE_OLD, exist_ok=True)

    # 1. Arsipkan Sishin_l2d lama (bukan versi_baru)
    for name in OLD_SISHIN_L2D:
        src = os.path.join(SISHIN, name)
        if os.path.exists(src):
            dst = os.path.join(ARCHIVE_OLD, name)
            if os.path.isdir(src):
                _copy_tree(src, dst)
                shutil.rmtree(src)
            else:
                shutil.copy2(src, dst)
                os.remove(src)
            print(f"[ARCHIVE] {name}")

    # 2. Salin versi_baru dari sishin_custom → sishin/
    for name in VERSI_BARU_FILES:
        src = os.path.join(CUSTOM, name)
        dst = os.path.join(SISHIN, name)
        if not os.path.exists(src):
            print(f"[SKIP] tidak ada: {src}")
            continue
        _copy_tree(src, dst)
        print(f"[INSTALL] {name} -> sishin/")

    # 3. Folder gerakan khusus Sishin (export Cubism ke sini)
    motions_sishin = os.path.join(SISHIN, "motions_sishin")
    os.makedirs(motions_sishin, exist_ok=True)

    # 4. Arsipkan & hapus sishin_custom
    if os.path.isdir(CUSTOM):
        if os.path.exists(ARCHIVE_CUSTOM):
            shutil.rmtree(ARCHIVE_CUSTOM)
        shutil.copytree(CUSTOM, ARCHIVE_CUSTOM)
        shutil.rmtree(CUSTOM)
        print(f"[REMOVE] sishin_custom/ -> _archive/sishin_custom_removed/")

    print("[OK] Sishin Versi Baru terpasang di static/live2d/sishin/")


if __name__ == "__main__":
    main()
