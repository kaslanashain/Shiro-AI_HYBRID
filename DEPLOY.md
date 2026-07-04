# Deploy Shiro AI (Railway / VPS / Docker)

## Railway (recommended)

1. Push repo to GitHub
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Set environment variables (see `.env.example`):
   - `SECRET_KEY` — random string (required)
   - `GROQ_API_KEY` — for AI chat
   - `GEMINI_API_KEY` — optional, for image vision
   - `CORS_ORIGINS` — your Railway URL or `*`
4. Railway auto-detects `Dockerfile` or use `railway.toml`
5. Open generated URL

**Note:** Voicevox & Ollama tidak jalan di Railway cloud — pakai Groq + Edge TTS.

## Docker (VPS)

```bash
docker build -t shiro-ai .
docker run -p 8080:8080 \
  -e SECRET_KEY=your-secret \
  -e GROQ_API_KEY=gsk_... \
  -v shiro_data:/app/data \
  shiro-ai
```

Mount volume for SQLite DB persistence.

## Local production test

```bash
pip install gunicorn gevent gevent-websocket
gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
  -w 1 -b 0.0.0.0:5000 main:app
```

## New features

| Feature | Endpoint / UI |
|---------|----------------|
| Login/Register | Header chip → `/api/auth/*` |
| Story Mode | Tombol **Story** → `/api/story/*` |
| Live2D | `static/live2d/` — lihat README di folder |
| Premium UI | `static/css/premium.css` |
| Proactive chat | Auto poll `/initiative`, `/event` |

## Live2D setup

Taruh model `.model3.json` di:
- `static/live2d/shiro/shiro.model3.json`
- `static/live2d/sishin/sishin.model3.json`

Tanpa model → fallback PNG otomatis.
