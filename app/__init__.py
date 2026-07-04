import logging
import os
from flask import Flask
from app import config
from app.db import init_db
from app.routes import register_routes
from app.tts import voice_mgr

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")

def create_app():
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    init_db()

    voice_mgr.voicevox_url = config.VOICEVOX_URL
    voice_mgr.voicevox_available = voice_mgr._check_voicevox()

    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, "templates"),
        static_folder=os.path.join(config.BASE_DIR, "static"),
    )

    # DAETARKAN ROUTE HANYA SEKALI DI SINI
    register_routes(app)

    return app