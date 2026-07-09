from scripts.gguf_local import gguf_status, resolve_gguf_from_line


def test_gguf_status_keys():
    st = gguf_status()
    assert "part1_ok" in st
    assert "split_complete" in st


def test_resolve_gguf_returns_line_or_none():
    line = resolve_gguf_from_line()
    assert line is None or line.startswith("FROM ")
