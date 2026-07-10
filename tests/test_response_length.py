from app.response_length import decide_response_length, format_length_instruction


def test_short_greeting():
    mode, _ = decide_response_length("halo", "", "shiro", 50)
    assert mode == "short"


def test_long_curhat():
    mode, meta = decide_response_length(
        "Shiro, aku lagi galau banget nih bisa dengerin curhatanku?",
        "",
        "shiro",
        50,
    )
    assert mode == "long"
    assert meta["max_tokens"] >= 500


def test_medium_default():
    mode, _ = decide_response_length(
        "gimana harimu hari ini?",
        "",
        "sishin",
        50,
    )
    assert mode == "medium"


def test_explicit_singkat():
    mode, _ = decide_response_length("singkat aja ya", "", "shiro", 50)
    assert mode == "short"


def test_length_instruction_long():
    block = format_length_instruction("long", "shiro")
    assert "PANJANG" in block
    assert "6–12" in block
