"""Tests for voice command intent parsing and app resolution."""
from app.voice_commands import (
    build_character_callback,
    launch_application,
    list_available_apps,
    normalize_transcript,
    parse_launch_intent,
    process_launch_command,
    resolve_app_key,
)


def test_normalize_transcript_strips_wake_word():
    assert normalize_transcript("Shiro tolong buka chrome") == "buka chrome"
    assert normalize_transcript("Hey Sishin, open notepad") == "open notepad"


def test_parse_launch_intent_indonesian():
    intent = parse_launch_intent("tolong buka google chrome", "shiro")
    assert intent is not None
    assert "chrome" in intent.app_query.lower()


def test_parse_launch_intent_english():
    intent = parse_launch_intent("open spotify please", "sishin")
    assert intent is not None
    assert "spotify" in intent.app_query.lower()


def test_parse_launch_intent_bisakah():
    intent = parse_launch_intent("bisakah kamu buka notepad", "shiro")
    assert intent is not None
    assert "notepad" in intent.app_query.lower()


def test_parse_launch_intent_software_keyword():
    intent = parse_launch_intent("tolong buka software spotify dong", "sishin")
    assert intent is not None
    assert "spotify" in intent.app_query.lower()


def test_resolve_app_key_fuzzy():
    key, score = resolve_app_key("kalkulator")
    assert key == "calculator"
    assert score > 0


def test_resolve_app_key_cursor():
    key, score = resolve_app_key("cursor")
    assert key == "cursor"
    assert score > 0


def test_parse_launch_intent_cursor():
    intent = parse_launch_intent("buka cursor", "shiro")
    assert intent is not None
    assert intent.app_query.lower() == "cursor"


def test_character_callback_success():
    from app.voice_commands import LaunchResult

    result = LaunchResult(ok=True, status="success", app_label="Notepad")
    out = build_character_callback(result, "shiro")
    assert "Notepad" in out.text
    assert "Sayang" in out.text or "bukakan" in out.text


def test_character_callback_not_found_sishin():
    from app.voice_commands import LaunchResult

    result = LaunchResult(ok=False, status="not_found", app_label="UnknownApp")
    out = build_character_callback(result, "sishin")
    assert "UnknownApp" in out.text
    assert "Kak" in out.text


def test_process_launch_command_returns_none_for_chat():
    assert process_launch_command("hai shiro apa kabar", "shiro") is None


def test_character_callback_sishin_success():
    from app.voice_commands import LaunchResult

    result = LaunchResult(ok=True, status="success", app_label="Spotify")
    out = build_character_callback(result, "sishin")
    assert "Spotify" in out.text
    assert "Kak" in out.text or "hore" in out.text.lower()


def test_list_available_apps():
    apps = list_available_apps()
    assert any(a["key"] == "notepad" for a in apps)
