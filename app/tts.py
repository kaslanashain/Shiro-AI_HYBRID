import asyncio
import logging
import os
import threading
import time

from app.config import MAX_TTS_FILES, TEMP_DIR, TTS_FILE_AGE_LIMIT
from voice_manager import VoiceManager

logger = logging.getLogger(__name__)

voice_mgr = VoiceManager(temp_dir=TEMP_DIR)
_tts_loop = None
_tts_loop_lock = threading.Lock()


def _get_tts_loop():
    global _tts_loop
    with _tts_loop_lock:
        if _tts_loop is None or _tts_loop.is_closed():
            _tts_loop = asyncio.new_event_loop()
            thread = threading.Thread(target=_tts_loop.run_forever, daemon=True)
            thread.start()
        return _tts_loop


async def generate_speech_async(teks, karakter="shiro"):
    if not teks or not teks.strip():
        return None
    from app.utils import bersihkan_teks_tts

    teks_clean = bersihkan_teks_tts(teks)
    if not teks_clean.strip():
        return None
    file_path = await voice_mgr.generate(teks_clean, karakter)
    if file_path and os.path.exists(file_path):
        return file_path
    return None


def generate_speech(teks, karakter="shiro"):
    loop = _get_tts_loop()
    future = asyncio.run_coroutine_threadsafe(generate_speech_async(teks, karakter), loop)
    return future.result(timeout=120)


def cleanup_old_tts_files():
    try:
        if not os.path.exists(TEMP_DIR):
            return
        files = [f for f in os.listdir(TEMP_DIR) if f.endswith((".wav", ".mp3"))]
        if len(files) > MAX_TTS_FILES:
            files_with_time = sorted(
                ((os.path.join(TEMP_DIR, f), os.path.getmtime(os.path.join(TEMP_DIR, f))) for f in files),
                key=lambda x: x[1],
            )
            for path, _ in files_with_time[: len(files_with_time) - MAX_TTS_FILES]:
                try:
                    os.remove(path)
                except OSError as exc:
                    logger.debug("Could not remove %s: %s", path, exc)
        current_time = time.time()
        for f in files:
            path = os.path.join(TEMP_DIR, f)
            if os.path.exists(path) and current_time - os.path.getmtime(path) > TTS_FILE_AGE_LIMIT:
                try:
                    os.remove(path)
                except OSError as exc:
                    logger.debug("Could not remove %s: %s", path, exc)
    except OSError as exc:
        logger.warning("TTS cleanup failed: %s", exc)


def start_cleanup_scheduler():
    def scheduler():
        while True:
            time.sleep(300)
            cleanup_old_tts_files()

    threading.Thread(target=scheduler, daemon=True).start()
