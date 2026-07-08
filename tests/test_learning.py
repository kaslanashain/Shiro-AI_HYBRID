import pytest

from app.learning import (
    extract_learnings,
    format_learnings_block,
    maybe_learn_from_turn,
    score_interaction_value,
)
from app.db import init_db, muat_pembelajaran, simpan_pembelajaran


@pytest.fixture(autouse=True)
def _ensure_db():
    init_db()


def test_score_low_for_short_ack():
    assert score_interaction_value("ok") < 0.35
    assert score_interaction_value("halo") < 0.45


def test_score_higher_for_personal_info():
    low = score_interaction_value("ok")
    high = score_interaction_value("Aku suka anime dan biasanya main game setiap malam")
    assert high > low
    assert high >= 0.55


def test_score_skips_voice_command():
    assert score_interaction_value("buka notepad") < 0.3


def test_extract_preference():
    items = extract_learnings("Aku suka kopi panjang setiap pagi", "shiro")
    assert any(i["category"] == "preference" and "kopi" in i["content"].lower() for i in items)


def test_extract_fact_hobby():
    items = extract_learnings("Hobi aku main gitar", "sishin")
    assert any(i["category"] == "preference" for i in items)


def test_soft_filter_allows_meaningful_greeting_with_content():
    score = score_interaction_value("Halo Shiro, aku lagi senang banget hari ini")
    assert score >= 0.28


def test_maybe_learn_persists_preference(tmp_path, monkeypatch):
    import app.db as db_mod
    test_db = tmp_path / "test_learn.db"
    monkeypatch.setattr(db_mod, "DB_PATH", str(test_db))
    init_db()

    maybe_learn_from_turn(
        "Aku suka programming Python",
        "Wah keren banget Sayang!",
        "shiro",
        user_id=1,
        profile={"fallback": "Maaf Sayang, Shiro agak bingung. Bisa diulang?"},
    )

    rows = muat_pembelajaran(user_id=1, karakter="shiro", limit=5, min_confidence=0.3)
    assert any("programming" in r["content"].lower() or "python" in r["content"].lower() for r in rows)


def test_dedup_increases_confidence(tmp_path, monkeypatch):
    import app.db as db_mod
    test_db = tmp_path / "test_dedup.db"
    monkeypatch.setattr(db_mod, "DB_PATH", str(test_db))
    init_db()

    simpan_pembelajaran(user_id=1, content="Suka kopi", category="preference", confidence=0.6, value_score=0.5)
    simpan_pembelajaran(user_id=1, content="Suka kopi", category="preference", confidence=0.6, value_score=0.5)

    rows = muat_pembelajaran(user_id=1, karakter="shiro", limit=5, min_confidence=0.3)
    assert len(rows) == 1
    assert rows[0]["confidence"] > 0.6


def test_format_learnings_block_empty():
    assert format_learnings_block("shiro", user_id=99999) == ""
