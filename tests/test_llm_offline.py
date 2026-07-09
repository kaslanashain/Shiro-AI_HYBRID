import pytest

from app import config
from app.llm_offline import enrich_offline_messages, offline_options, resolve_ollama_model


def test_resolve_ollama_model_per_character():
    assert resolve_ollama_model("shiro") == config.OLLAMA_MODEL_SHIRO
    if config.OLLAMA_OFFLINE_SHARED:
        assert resolve_ollama_model("sishin") == config.OLLAMA_MODEL_SHIRO
    else:
        assert resolve_ollama_model("sishin") == config.OLLAMA_MODEL_SISHIN
    assert resolve_ollama_model("unknown") == config.OLLAMA_MODEL


def test_offline_options_smarter_than_legacy():
    opts = offline_options()
    assert opts["temperature"] >= 0.5
    assert opts["num_predict"] <= 256
    assert opts["num_ctx"] <= 8192


def test_enrich_offline_messages_inserts_few_shot():
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "halo"},
    ]
    out = enrich_offline_messages(messages, "shiro")
    assert out[0]["role"] == "system"
    assert out[1]["role"] == "user"
    assert out[2]["role"] == "assistant"
    assert "teks_layar" in out[2]["content"]
    assert out[-1]["content"] == "halo"


def test_enrich_offline_messages_sishin():
    messages = [{"role": "user", "content": "test"}]
    out = enrich_offline_messages(messages, "sishin")
    assert any(m["role"] == "assistant" and "Hore" in m["content"] for m in out)
