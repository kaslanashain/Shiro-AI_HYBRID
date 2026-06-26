import logging
import os

from flask import Flask

from app import config
from app.db import close_db, init_db
from app.routes import register_routes
from app.tts import cleanup_old_tts_files, start_cleanup_scheduler, voice_mgr

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)


def create_app():
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    init_db()

    from app import config as cfg

    voice_mgr.voicevox_url = cfg.VOICEVOX_URL
    voice_mgr.voicevox_available = voice_mgr._check_voicevox()

    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, "templates"),
        static_folder=os.path.join(config.BASE_DIR, "static"),
    )
    app.teardown_appcontext(close_db)
    register_routes(app)
    return app
