"""Download official Live2D sample models (Haru, Hiyori) into static/live2d/."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "Live2D/CubismWebSamples"
BRANCH = "develop"
BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "Samples/Resources/Haru": ROOT / "static/live2d/shiro",
    "Samples/Resources/Hiyori": ROOT / "static/live2d/sishin",
}


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.load(resp)


def list_files(prefix: str) -> list[str]:
    data = fetch_json(
        f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
    )
    files: list[str] = []
    for item in data.get("tree", []):
        path = item.get("path", "")
        if path.startswith(prefix + "/") and item.get("type") == "blob":
            files.append(path)
    return files


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Shiro-AI-Live2D-Installer"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def install_pair(source_prefix: str, dest_root: Path) -> int:
    files = list_files(source_prefix)
    if not files:
        print(f"No files found for {source_prefix}", file=sys.stderr)
        return 1

    ok = 0
    for remote_path in files:
        rel = remote_path[len(source_prefix) + 1 :]
        dest = dest_root / rel
        url = f"{BASE}/{remote_path}"
        try:
            print(f"  {rel}")
            download(url, dest)
            ok += 1
        except urllib.error.URLError as exc:
            print(f"  FAILED {rel}: {exc}", file=sys.stderr)
    print(f"Installed {ok}/{len(files)} files -> {dest_root}")
    return 0 if ok == len(files) else 2


def main() -> int:
    print("Live2D sample installer (Haru -> shiro, Hiyori -> sishin)")
    print("License: Live2D Free Material License — dev/testing only.\n")
    code = 0
    for prefix, dest in TARGETS.items():
        print(prefix)
        code = max(code, install_pair(prefix, dest))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
