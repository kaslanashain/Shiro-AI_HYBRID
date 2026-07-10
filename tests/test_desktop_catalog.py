"""Tests for desktop read-only catalog indexing."""
import os
import sys
from unittest.mock import patch

import pytest

from app.app_catalog import (
    _read_lnk_target,
    _scan_desktop_readonly,
    find_desktop_item,
    get_launch_registry,
    invalidate_catalog_cache,
    resolve_launch_path,
)


@pytest.fixture(autouse=True)
def _clear_catalog_cache():
    invalidate_catalog_cache()
    yield
    invalidate_catalog_cache()


def test_scan_desktop_indexes_shortcut(monkeypatch, tmp_path):
    if sys.platform != "win32":
        pytest.skip("Windows only")

    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    lnk = desktop / "Cursor.lnk"
    lnk.write_bytes(b"fake")

    monkeypatch.setattr(
        "app.app_catalog._desktop_directories",
        lambda: [str(desktop)],
    )
    monkeypatch.setattr(
        "app.app_catalog._read_lnk_target",
        lambda p: r"C:\Apps\Cursor.exe" if str(p).endswith("Cursor.lnk") else None,
    )

    items = _scan_desktop_readonly(force_refresh=True)
    assert any(e.get("label") == "Cursor" for e in items.values())
    cursor = next(e for e in items.values() if e.get("label") == "Cursor")
    assert cursor.get("shortcut") == str(lnk)
    assert cursor.get("path") == r"C:\Apps\Cursor.exe"


def test_resolve_launch_path_prefers_shortcut_when_exe_missing(tmp_path):
    lnk = tmp_path / "Cursor.lnk"
    lnk.write_bytes(b"x")
    entry = {
        "label": "Cursor",
        "shortcut": str(lnk),
        "path": r"C:\missing\Cursor.exe",
        "type": "app",
    }
    with patch("app.app_catalog.os.path.exists", return_value=False):
        with patch("app.app_catalog.os.path.isfile", side_effect=lambda p: str(p).endswith(".lnk")):
            assert resolve_launch_path(entry) == str(lnk)


def test_find_desktop_item_cursor(monkeypatch, tmp_path):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    fake_items = {
        "desk_cursor": {
            "label": "Cursor",
            "shortcut": str(desktop / "Cursor.lnk"),
            "type": "app",
            "aliases": ["cursor"],
        }
    }
    monkeypatch.setattr("app.app_catalog._scan_desktop_readonly", lambda **_: fake_items)
    key, entry, score = find_desktop_item("cursor")
    assert key == "desk_cursor"
    assert entry["label"] == "Cursor"
    assert score > 0


def test_launch_registry_merges_desktop_cursor(monkeypatch):
    fake_desktop = {
        "desk_cursor": {
            "label": "Cursor",
            "shortcut": r"C:\Users\asus\Desktop\Cursor.lnk",
            "path": r"C:\Users\asus\Desktop\Cursor.lnk",
            "type": "app",
            "aliases": ["cursor"],
            "source": "desktop",
        }
    }
    monkeypatch.setattr("app.app_catalog._scan_desktop_readonly", lambda **_: fake_desktop)
    monkeypatch.setattr(
        "app.app_catalog.resolve_catalog_path",
        lambda entry: None if entry.get("source") == "builtin" else entry.get("shortcut"),
    )
    monkeypatch.setattr(
        "app.app_catalog.resolve_launch_path",
        lambda entry: entry.get("shortcut"),
    )
    reg = get_launch_registry(force_refresh=True)
    assert "cursor" in reg
    assert reg["cursor"].get("shortcut")
