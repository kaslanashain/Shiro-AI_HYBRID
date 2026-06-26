import pytest

from app.chat import resolve_character
from app.utils import (
    bersihkan_teks_tts,
    detect_input_language,
    parse_json_response,
    saring_bahasa_alien,
    sync_text_and_voice,
    validasi_respon_teks,
)


def test_detect_japanese():
    assert detect_input_language("こんにちは") == "ja"
    assert detect_input_language("Halo sayang") == "id"


def test_parse_json_response():
    raw = 'Some text {"teks_layar": "Hai", "teks_suara": "Hai"} trailing'
    parsed = parse_json_response(raw)
    assert parsed["teks_layar"] == "Hai"


def test_saring_bahasa_alien_blocks_code():
    assert "bingung" in saring_bahasa_alien("def foo(): pass")


def test_sync_text_and_voice_uses_suara():
    layar, suara = sync_text_and_voice("Halo 😊", "Halo")
    assert layar == "Halo 😊"
    assert "😊" not in suara


def test_validasi_respon_teks_rejects_long():
    assert validasi_respon_teks("x" * 301, "") is False


def test_resolve_character_prefers_keyword():
    assert resolve_character("halo sishin") == "sishin"
    assert resolve_character("halo shiro") == "shiro"


def test_resolve_character_uses_preferred():
    assert resolve_character("halo", preferred="sishin") == "sishin"


def test_bersihkan_teks_tts():
    assert bersihkan_teks_tts("test 🐱") == "test"
