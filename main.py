import logging
import os
import base64
import sys
import signal
import time
import concurrent.futures
import threading
from flask import request
from flask_socketio import SocketIO, emit
from app import create_app
from app.chat import jawab_shiro
from app.tts import cleanup_old_tts_files, start_cleanup_scheduler, generate_speech
from app.voice import transcribe_audio
from app import config

# ===== KONFIGURASI LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== BUAT APP =====
app = create_app()

# ===== INISIALISASI SOCKETIO =====
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="gevent",
    ping_interval=25,
    ping_timeout=60,
    logger=logger,
    engineio_logger=False
)
logger.info("SocketIO initialized with gevent async mode")

# ===== FLAG UNTUK MENCEGAH PROSES BERSAMAAN =====
_processing_audio = False
_last_audio_time = 0
_processing_lock = threading.Lock()

# ===== WEBSOCKET EVENTS =====

@socketio.on("connect")
def handle_connect():
    try:
        logger.info("Client connected: %s", request.sid)
        emit("connected", {"status": "connected"})
    except Exception as e:
        logger.exception("Error in connect handler: %s", e)

@socketio.on("disconnect")
def handle_disconnect():
    try:
        logger.info("Client disconnected: %s", request.sid)
    except Exception as e:
        logger.exception("Error in disconnect handler: %s", e)

@socketio.on("audio")
def handle_audio(data):
    """Handle audio from client: STT → AI → TTS → reply"""
    global _processing_audio, _last_audio_time
    
    # Cegah spam audio - minimal jeda 500ms
    current_time = time.time()
    if current_time - _last_audio_time < 0.5:
        logger.debug("Audio terlalu cepat, diabaikan")
        return
    _last_audio_time = current_time
    
    # Cegah proses bersamaan
    with _processing_lock:
        if _processing_audio:
            logger.warning("Audio masih diproses, abaikan")
            emit("error", {"message": "Masih memproses audio sebelumnya"})
            return
        _processing_audio = True
    
    # Tangkap sid client di thread utama
    client_sid = request.sid
    
    try:
        # 1. Validasi input
        audio_b64 = data.get("audio")
        if not audio_b64:
            logger.warning("No audio data received")
            emit("error", {"message": "Tidak ada data audio"})
            with _processing_lock:
                _processing_audio = False
            return

        # 2. Decode audio
        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception as e:
            logger.error("Base64 decode error: %s", e)
            emit("error", {"message": "Format audio tidak valid"})
            with _processing_lock:
                _processing_audio = False
            return

        if len(audio_bytes) < 100:
            logger.warning("Audio terlalu pendek: %d bytes", len(audio_bytes))
            emit("error", {"message": "Audio terlalu pendek"})
            with _processing_lock:
                _processing_audio = False
            return
        
        # 3. Proses di background
        def process_audio():
            try:
                # 3a. Speech-to-Text
                try:
                    text = transcribe_audio(audio_bytes)
                except Exception as e:
                    logger.exception("STT error: %s", e)
                    text = None

                if not text:
                    logger.warning("Transcription failed atau kosong")
                    socketio.emit("error", {"message": "Gagal mengenali suara"}, room=client_sid)
                    return

                logger.info("User said: %s", text)

                # 3b. Proses AI
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(jawab_shiro, text)
                        result, status = future.result(timeout=15)
                except concurrent.futures.TimeoutError:
                    logger.error("AI response timeout setelah 15 detik")
                    socketio.emit("error", {"message": "AI terlalu lama merespons"}, room=client_sid)
                    return
                except Exception as e:
                    logger.exception("AI processing error: %s", e)
                    socketio.emit("error", {"message": "Gagal memproses permintaan"}, room=client_sid)
                    return

                reply = result.get("text", "Maaf, aku tidak mengerti.")
                karakter = result.get("karakter", "shiro")
                logger.info("AI reply: %s (karakter: %s)", reply[:50], karakter)

                # 3c. Text-to-Speech
                try:
                    audio_file = generate_speech(reply, karakter)
                except Exception as e:
                    logger.exception("TTS error: %s", e)
                    socketio.emit("response", {"text": reply, "audio": None, "karakter": karakter}, room=client_sid)
                    return

                if not audio_file or not os.path.exists(audio_file):
                    logger.warning("TTS file not generated")
                    socketio.emit("response", {"text": reply, "audio": None, "karakter": karakter}, room=client_sid)
                    return

                # 3d. Kirim audio balasan
                try:
                    with open(audio_file, "rb") as f:
                        audio_data = f.read()
                    audio_base64 = base64.b64encode(audio_data).decode("utf-8")
                    socketio.emit("response", {"text": reply, "audio": audio_base64, "karakter": karakter}, room=client_sid)
                    logger.info("Response sent with audio (%d bytes)", len(audio_data))
                except Exception as e:
                    logger.exception("Error reading TTS file: %s", e)
                    socketio.emit("response", {"text": reply, "audio": None, "karakter": karakter}, room=client_sid)

                # 3e. Cleanup file TTS
                try:
                    if os.path.exists(audio_file):
                        os.unlink(audio_file)
                        logger.debug("TTS file cleaned: %s", audio_file)
                except Exception as e:
                    logger.warning("Cleanup TTS file error: %s", e)

            except Exception as e:
                logger.exception("Unexpected error in process_audio: %s", e)
                try:
                    socketio.emit("error", {"message": "Terjadi kesalahan internal"}, room=client_sid)
                except:
                    pass
            finally:
                with _processing_lock:
                    global _processing_audio
                    _processing_audio = False

        # Jalankan di thread terpisah
        thread = threading.Thread(target=process_audio, daemon=True)
        thread.start()
        
    except Exception as e:
        logger.exception("Unexpected error in handle_audio: %s", e)
        with _processing_lock:
            _processing_audio = False
        try:
            emit("error", {"message": "Terjadi kesalahan internal"})
        except:
            pass


# ===== EVENT UNTUK TEST PING (OPSIONAL) =====
@socketio.on("ping")
def handle_ping():
    emit("pong", {"time": time.time()})

# ===== SHUTDOWN HANDLER =====
def signal_handler(sig, frame):
    logger.info("Shutting down gracefully...")
    socketio.stop()
    sys.exit(0)

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Shiro AI System Initialized")
    logger.info("Voice: Edge TTS (ID) + Voicevox (JP)")
    logger.info("Ollama model: %s", config.OLLAMA_MODEL)
    logger.info("=" * 60)

    start_cleanup_scheduler()
    cleanup_old_tts_files()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        socketio.run(
            app,
            debug=config.FLASK_DEBUG,
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        logger.info("Server dihentikan oleh user")
    except Exception as e:
        logger.exception("Server error: %s", e)
    finally:
        logger.info("Server shutdown complete")