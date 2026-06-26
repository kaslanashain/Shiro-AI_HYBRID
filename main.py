"""Shiro AI entry point."""
import logging

from app import config, create_app
from app.chat import deskripsi_gambar, jawab_shiro
from app.tts import cleanup_old_tts_files, start_cleanup_scheduler

logger = logging.getLogger(__name__)

app = create_app()

__all__ = ["app", "jawab_shiro", "deskripsi_gambar"]


if __name__ == "__main__":
    logger.info("Shiro AI System Initialized")
    logger.info("Voice: Edge TTS (ID) + Voicevox (JP)")
    logger.info("Ollama model: %s", config.OLLAMA_MODEL)

    start_cleanup_scheduler()
    cleanup_old_tts_files()

    app.run(debug=config.FLASK_DEBUG, host=config.FLASK_HOST, port=config.FLASK_PORT)
