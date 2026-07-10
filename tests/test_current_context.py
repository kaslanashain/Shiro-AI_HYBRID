from app.current_context import (
    format_world_context_block,
    get_now,
    weather_code_label,
    world_context_for_validation,
)


def test_weather_code_label():
    assert weather_code_label(0) == "cerah"
    assert weather_code_label(61) == "hujan"
    assert weather_code_label(95) == "badai petir"


def test_format_world_context_block_contains_time():
    block = format_world_context_block("shiro")
    now = get_now()
    assert "INFORMASI DUNIA NYATA" in block
    assert str(now.year) in block
    assert "WIB" in block
    assert "Cuaca" in block or "cuaca" in block.lower()


def test_world_context_for_validation_allows_time_words():
    ctx = world_context_for_validation()
    assert "tahun" in ctx
    assert "cuaca" in ctx
