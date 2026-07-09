"""Offline LLM backend — model Shiro & Sishin via Ollama."""
import logging
import os

import ollama

from app import config

logger = logging.getLogger(__name__)

# Satu contoh few-shot (cukup untuk format JSON, tidak membebani ctx)
_FEW_SHOT = {
    "shiro": [
        {"role": "user", "content": "Sayang, aku kangen"},
        {
            "role": "assistant",
            "content": (
                '{"teks_layar": "Aku juga kangen banget, Sayang~", '
                '"teks_suara": "Aku juga kangen banget Sayang"}'
            ),
        },
    ],
    "sishin": [
        {"role": "user", "content": "Sishin, main yuk!"},
        {
            "role": "assistant",
            "content": (
                '{"teks_layar": "Hore! Mau banget Kak~", '
                '"teks_suara": "Hore! Mau banget Kak"}'
            ),
        },
    ],
}


def resolve_ollama_model(karakter: str) -> str:
    """Pilih model Ollama — shared mode hindari reload antar karakter."""
    if config.OLLAMA_OFFLINE_SHARED:
        return config.OLLAMA_MODEL_SHIRO
    if karakter == "sishin":
        return config.OLLAMA_MODEL_SISHIN
    if karakter == "shiro":
        return config.OLLAMA_MODEL_SHIRO
    return config.OLLAMA_MODEL


def offline_options() -> dict:
    return dict(config.OLLAMA_OFFLINE_OPTIONS)


def enrich_offline_messages(messages: list, karakter: str) -> list:
    """Sisipkan 1 few-shot singkat setelah system prompt."""
    if not messages:
        return messages

    system_msg = messages[0] if messages[0].get("role") == "system" else None
    rest = messages[1:] if system_msg else messages
    few_shot = _FEW_SHOT.get(karakter, _FEW_SHOT["shiro"])

    enriched = []
    if system_msg:
        enriched.append(system_msg)
    enriched.extend(few_shot)
    # Batasi riwayat chat agar prompt tidak membengkak di CPU
    history = rest[-8:] if len(rest) > 8 else rest
    enriched.extend(history)
    return enriched


def check_ollama_models() -> dict:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    result = {"host": host, "shiro": False, "sishin": False, "models": []}
    try:
        client = ollama.Client(host=host)
        listed = client.list()
        names = set()
        for item in listed.get("models", []):
            name = item.get("name") or item.get("model") or ""
            names.add(name.split(":")[0])
            result["models"].append(name)
        result["shiro"] = resolve_ollama_model("shiro").split(":")[0] in names
        result["sishin"] = (
            resolve_ollama_model("sishin").split(":")[0] in names
            if not config.OLLAMA_OFFLINE_SHARED
            else result["shiro"]
        )
    except Exception as exc:
        logger.warning("Ollama tidak terjangkau: %s", exc)
        result["error"] = str(exc)
    return result


def warmup_offline_model(karakter: str = "shiro") -> bool:
    """Muat model ke RAM sekali saat startup — chat pertama tidak menunggu load."""
    try:
        client = ollama.Client(host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
        model = resolve_ollama_model(karakter)
        client.chat(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            options={"num_predict": 1, "num_ctx": 512},
            keep_alive=config.OLLAMA_KEEP_ALIVE,
        )
        logger.info("[OFF] Model %s preloaded (keep_alive=%s)", model, config.OLLAMA_KEEP_ALIVE)
        return True
    except Exception as exc:
        logger.warning("[OFF] Warmup gagal: %s", exc)
        return False


def call_ollama_offline(
    messages: list,
    karakter: str = "shiro",
    *,
    stream: bool = False,
    on_token=None,
) -> dict:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    client = ollama.Client(host=host)
    model = resolve_ollama_model(karakter)
    options = offline_options()
    payload = enrich_offline_messages(messages, karakter)
    keep_alive = config.OLLAMA_KEEP_ALIVE

    logger.info(
        "[OFF] Ollama model=%s karakter=%s ctx=%s predict=%s",
        model, karakter, options.get("num_ctx"), options.get("num_predict"),
    )

    if stream and on_token:
        full = ""
        stream_resp = client.chat(
            model=model,
            messages=payload,
            options=options,
            stream=True,
            keep_alive=keep_alive,
        )
        for chunk in stream_resp:
            delta = (chunk.get("message") or {}).get("content") or ""
            if delta:
                full += delta
                on_token(delta, full)
        return {"message": {"content": full}}

    response = client.chat(
        model=model,
        messages=payload,
        options=options,
        keep_alive=keep_alive,
    )
    content = (response.get("message") or {}).get("content", "")
    if on_token and content:
        on_token(content, content)
    return response
