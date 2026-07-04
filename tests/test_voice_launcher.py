"""Tests for voice-command app launcher."""
from app.voice_launcher import (
    build_character_response,
    list_catalog,
    parse_launch_intent,
    process_voice_command,
    resolve_app_target,
)


def test_parse_launch_intent_indonesian():
    intent = parse_launch_intent("Tolong buka notepad")
    assert intent is not None
    assert "notepad" in intent.app_query


def test_parse_launch_intent_english():
    intent = parse_launch_intent("Open Google Chrome please")
    assert intent is not None
    assert "chrome" in intent.app_query or "google" in intent.app_query


def test_parse_launch_intent_with_wake_word():
    intent = parse_launch_intent("Shiro tolong buka kalkulator")
    assert intent is not None
    assert "kalkulator" in intent.app_query or "calc" in intent.app_query


def test_parse_launch_intent_not_command():
    assert parse_launch_intent("Kamu lucu banget hari ini") is None


def test_resolve_app_target_fuzzy():
    target = resolve_app_target("kalkulator")
    assert target is not None
    assert target.app_id == "calculator"


def test_resolve_app_target_chrome():
    target = resolve_app_target("chrome")
    assert target is None or target.app_id == "chrome"


def test_build_character_response_shiro_success():
    text, suara = build_character_response("success", "shiro", app_label="Notepad")
    assert "Notepad" in text
    assert "Sayang" in text


def test_build_character_response_sishin_not_found():
    text, suara = build_character_response("not_found", "sishin", app_query="xyzapp")
    assert "xyzapp" in text
    assert "Kak" in text


def test_process_voice_command_not_intent():
    result = process_voice_command("Halo sayang apa kabar", "shiro")
    assert result.handled is False
    assert result.status == "not_intent"


def test_process_voice_command_launch_notepad():
    result = process_voice_command("buka notepad", "shiro")
    assert result.handled is True
    # May succeed or fail depending on OS in CI; status should be valid
    assert result.status in ("success", "error", "not_found")


def test_list_catalog_nonempty():
    catalog = list_catalog()
    assert len(catalog) >= 5
    assert any(item["id"] == "notepad" for item in catalog)
