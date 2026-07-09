"""Tests for companion presence helpers."""
from app.companion_presence import music_companion_reply


def test_music_companion_opinion_prompt():
    reply, _status = music_companion_reply("Lagu Santai", "shiro", "opinion")
    assert reply.get("text")


def test_music_companion_sing_prompt():
    reply, _status = music_companion_reply("bgm_1", "sishin", "sing")
    assert reply.get("text")
