# Shiro-AI_HYBRID

Hybrid AI companion (Shiro & Sishin) with local Ollama chat, Gemini vision, Edge TTS, and Voicevox.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set OLLAMA_MODEL and optional GEMINI_API_KEY
py main.py
```

Open http://127.0.0.1:5000

## Requirements

- [Ollama](https://ollama.com/) with a chat model (`gemma2:2b`, `qwen2.5:7b`, etc.)
- Optional: [VOICEVOX](https://voicevox.hiroshiba.jp/) on port 50021 for Japanese voice
- Optional: `GEMINI_API_KEY` for image descriptions

## Project layout

```
app/
  config.py    # Environment settings
  db.py        # SQLite memory & status
  chat.py      # Character AI logic
  routes.py    # Flask endpoints
  tts.py       # Speech generation
  utils.py     # Text/JSON helpers
main.py        # Entry point
templates/     # Web UI
static/js/     # Frontend
voice_manager.py
```

## API

| Endpoint | Method | Body |
|----------|--------|------|
| `/chat` | POST | `{ "message", "karakter" }` |
| `/tts` | POST | `{ "text", "karakter" }` |
| `/upload` | POST | multipart: `image`, `karakter`, `caption` |
| `/voice` | POST | `{ "text", "karakter" }` (client STT) |
| `/sawer` | POST | `{ "amount", "karakter" }` |
| `/status` | GET | — |

## Tests

```bash
py -m pytest tests/ -q
```
