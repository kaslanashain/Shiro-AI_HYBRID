# tts.py
import asyncio
import logging
import os
import threading
import time
import concurrent.futures

from app.config import MAX_TTS_FILES, TEMP_DIR, TTS_FILE_AGE_LIMIT
from voice_manager import VoiceManager

logger = logging.getLogger(__name__)

voice_mgr = VoiceManager(temp_dir=TEMP_DIR)
_tts_loop = None
_tts_loop_lock = threading.Lock()


def _get_tts_loop():
    """Mendapatkan atau membuat event loop khusus untuk TTS"""
    global _tts_loop
    with _tts_loop_lock:
        if _tts_loop is None or _tts_loop.is_closed():
            _tts_loop = asyncio.new_event_loop()
            thread = threading.Thread(target=_tts_loop.run_forever, daemon=True)
            thread.start()
            logger.info("TTS event loop started")
        return _tts_loop


async def generate_speech_async(teks, karakter="shiro"):
    """Generate suara secara asinkron"""
    if not teks or not teks.strip():
        return None

    # Bersihkan teks (fungsi ini harus ada di app.utils)
    try:
        from app.utils import bersihkan_teks_tts
        teks_clean = bersihkan_teks_tts(teks)
    except ImportError:
        # Fallback jika fungsi tidak ditemukan
        teks_clean = teks.strip()
        logger.warning("bersihkan_teks_tts tidak ditemukan, pakai teks asli")

    if not teks_clean.strip():
        return None

    file_path = await voice_mgr.generate(teks_clean, karakter)
    if file_path and os.path.exists(file_path):
        logger.debug("TTS generated: %s", file_path)
        return file_path
    return None


def generate_speech(teks, karakter="shiro"):
    """
    Generate suara secara sinkron (blokir) - dipanggil dari thread utama.
    Menggunakan event loop terpisah agar tidak mengganggu main loop.
    """
    if not teks or not teks.strip():
        return None

    loop = _get_tts_loop()
    future = asyncio.run_coroutine_threadsafe(
        generate_speech_async(teks, karakter), loop
    )
    try:
        return future.result(timeout=120)  # timeout 120 detik
    except concurrent.futures.TimeoutError:
        logger.error("TTS generation timeout setelah 120 detik")
        return None
    except Exception as e:
        logger.exception("TTS generation error: %s", e)
        return None


def cleanup_old_tts_files():
    """Hapus file TTS lama untuk menjaga ukuran folder"""
    try:
        if not os.path.exists(TEMP_DIR):
            return

        files = [f for f in os.listdir(TEMP_DIR) if f.endswith((".wav", ".mp3"))]
        if not files:
            return

        # Urutkan berdasarkan waktu modifikasi
        files_with_time = sorted(
            ((os.path.join(TEMP_DIR, f), os.path.getmtime(os.path.join(TEMP_DIR, f))) for f in files),
            key=lambda x: x[1],
        )

        # Hapus file berlebih (di atas MAX_TTS_FILES)
        if len(files_with_time) > MAX_TTS_FILES:
            for path, _ in files_with_time[:len(files_with_time) - MAX_TTS_FILES]:
                try:
                    os.remove(path)
                    logger.debug("Removed old TTS: %s", path)
                except OSError as exc:
                    logger.debug("Could not remove %s: %s", path, exc)

        # Hapus file yang terlalu tua
        current_time = time.time()
        for path, mtime in files_with_time:
            if current_time - mtime > TTS_FILE_AGE_LIMIT:
                try:
                    os.remove(path)
                    logger.debug("Removed aged TTS: %s", path)
                except OSError as exc:
                    logger.debug("Could not remove %s: %s", path, exc)

    except Exception as exc:
        logger.warning("TTS cleanup gagal: %s", exc)


def start_cleanup_scheduler():
    """Jalankan scheduler untuk membersihkan file TTS setiap 5 menit"""
    def scheduler():
        while True:
            time.sleep(300)  # 5 menit
            cleanup_old_tts_files()

    threading.Thread(target=scheduler, daemon=True).start()
    logger.info("TTS cleanup scheduler started")