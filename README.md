# Shiro-AI_HYBRID

Hybrid AI companion (Shiro & Sishin) with local Ollama chat, Gemini vision, Edge TTS, Voicevox, Live2D wardrobe, and desktop tray app.

## Quick start

**Web:**
```bash
pip install -r requirements.txt
cp .env.example .env
py scripts/setup_ollama_models.py
py main.py
```

**Desktop (Windows):**
```bat
.\start_desktop.bat
```

Open http://127.0.0.1:5000

## Offline AI (Ollama)

- Default model: `qwen2.5:3b` (cepat di CPU)
- Persona: `shiro-ai`, `sishin-ai` — setup via `py scripts/setup_ollama_models.py`
- Arsip 7B: `models/Modelfile.shiro.7b`, `models/Modelfile.sishin.7b`

## Live2D wardrobe

| Karakter | Default | Sample Live2D | Custom upload |
|----------|---------|---------------|---------------|
| Shiro | Ekspresi PNG | Haru | `static/live2d/custom/shiro/` |
| Sishin | Ekspresi PNG | Hiyori | `static/live2d/custom/sishin/` |

```bash
py scripts/setup_live2d_layout.py    # atur folder sample + custom
py scripts/install_custom_l2d.py     # setelah upload model Cubism
```

Detail: `static/live2d/README.md`

## Requirements

- [Ollama](https://ollama.com/) with a chat model (`qwen2.5:3b` default offline, `qwen2.5:7b` arsip di `models/*.7b`)
- Optional: [VOICEVOX](https://voicevox.hiroshiba.jp/) on port 50021 for Japanese voice
- Optional: `GEMINI_API_KEY` for image descriptions

## Project layout

```
app/
  config.py    # Environment settings
  llm_offline.py  # Ollama routing & smart options
  chat.py      # Character AI logic
  routes.py    # Flask endpoints (+ /api/wardrobe/catalog)
main.py        # Entry point
scripts/       # setup_ollama_models, preflight_desktop, live2d installers
static/live2d/ # Haru, Hiyori samples + custom upload folders
static/vendor/ # Live2D libs (offline, no CDN)
templates/     # Web UI
desktop_launcher.py
start_desktop.bat
```

## API

| Endpoint | Method | Body |
|----------|--------|------|
| `/chat` | POST | `{ "message", "karakter" }` |
| `/api/wardrobe/catalog` | GET | outfit list (PNG + Live2D) |
| `/tts` | POST | `{ "text", "karakter" }` |
| `/upload` | POST | multipart: `image`, `karakter`, `caption` |
| `/voice` | POST | `{ "text", "karakter" }` (client STT) |
| `/sawer` | POST | `{ "amount", "karakter" }` |
| `/status` | GET | — |

## Tests

```bash
py -m pytest tests/ -q
```
