import logging
import os
import base64
import sys
import signal
import time
import concurrent.futures
import threading
from flask import request, jsonify
from flask_socketio import SocketIO, emit
from app import create_app
from app.chat import jawab_shiro, jawab_shiro_stream
from app.tts import cleanup_old_tts_files, start_cleanup_scheduler, generate_speech
from app.voice import transcribe_audio_with_retry, get_whisper_model
from app.voice_commands import process_launch_command
from app import config

# ===== KONFIGURASI LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== BUAT APP =====
app = create_app()

# Production: Railway/Heroku set PORT
if os.environ.get("PORT"):
    config.FLASK_PORT = int(os.environ["PORT"])
    config.FLASK_HOST = "0.0.0.0"

_cors = config.CORS_ORIGINS if config.CORS_ORIGINS != "*" else "*"

# ===== INISIALISASI SOCKETIO =====
socketio = SocketIO(
    app,
    cors_allowed_origins=_cors,
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


def _emit_character_response(
    client_sid: str,
    reply: str,
    suara_text: str,
    karakter: str,
    *,
    stream_msg_id: str | None = None,
    extra: dict | None = None,
):
    """Send text + TTS audio to client (voice / app-launcher replies)."""
    extra = extra or {}
    if stream_msg_id:
        socketio.emit(
            "stream_end",
            {"text": reply, "karakter": karakter, "msg_id": stream_msg_id, **extra},
            room=client_sid,
        )
    else:
        socketio.emit("stream_start", {"karakter": karakter}, room=client_sid)
        socketio.emit(
            "stream_end",
            {"text": reply, "karakter": karakter, **extra},
            room=client_sid,
        )

    try:
        audio_file = generate_speech(suara_text, karakter)
    except Exception as e:
        logger.exception("TTS error: %s", e)
        socketio.emit(
            "response",
            {"text": reply, "audio": None, "karakter": karakter, **extra},
            room=client_sid,
        )
        return

    if not audio_file or not os.path.exists(audio_file):
        socketio.emit(
            "response",
            {"text": reply, "audio": None, "karakter": karakter, **extra},
            room=client_sid,
        )
        return

    try:
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        socketio.emit(
            "response",
            {"text": reply, "audio": audio_base64, "karakter": karakter, **extra},
            room=client_sid,
        )
    except Exception as e:
        logger.exception("Error reading TTS file: %s", e)
        socketio.emit(
            "response",
            {"text": reply, "audio": None, "karakter": karakter, **extra},
            room=client_sid,
        )
    finally:
        try:
            if audio_file and os.path.exists(audio_file):
                os.unlink(audio_file)
        except Exception as e:
            logger.warning("Cleanup TTS file error: %s", e)


def _try_voice_app_launch(text: str, client_sid: str, karakter: str, enabled: bool = True) -> bool:
    """If utterance is an open-app command, launch it and reply in character. Returns True if handled."""
    if not enabled:
        return False

    launch = process_launch_command(text, karakter)
    if not launch:
        return False

    logger.info(
        "Voice command (%s): %s -> %s (%s)",
        karakter,
        text,
        launch.app_label or launch.app_key,
        launch.status,
    )
    socketio.emit("transcript", {"text": text, "karakter": karakter}, room=client_sid)
    socketio.emit("stream_start", {"karakter": karakter}, room=client_sid)
    socketio.emit(
        "voice_command",
        {
            "status": launch.status,
            "app_key": launch.app_key,
            "app_label": launch.app_label,
            "ok": launch.ok,
            "karakter": karakter,
        },
        room=client_sid,
    )
    _emit_character_response(
        client_sid,
        launch.text,
        launch.suara,
        karakter,
        extra={
            "voice_command": {
                "status": launch.status,
                "app_key": launch.app_key,
                "app_label": launch.app_label,
                "ok": launch.ok,
            }
        },
    )
    return True


def _process_voice_reply(
    text: str,
    client_sid: str,
    preferred_karakter: str = "shiro",
    voice_commands_enabled: bool = True,
):
    """AI + TTS pipeline shared by audio STT and voice_text events."""
    if not text or not text.strip():
        socketio.emit("error", {"message": "Teks kosong"}, room=client_sid)
        return

    if preferred_karakter not in ("shiro", "sishin"):
        preferred_karakter = "shiro"

    text = text.strip()
    logger.info("User said (%s): %s", preferred_karakter, text)

    if _try_voice_app_launch(text, client_sid, preferred_karakter, voice_commands_enabled):
        return

    socketio.emit("transcript", {"text": text, "karakter": preferred_karakter}, room=client_sid)
    socketio.emit("stream_start", {"karakter": preferred_karakter}, room=client_sid)

    stream_msg_id = "stream_" + client_sid[:8]

    def on_token(delta, full):
        try:
            socketio.emit(
                "stream_token",
                {
                    "token": delta,
                    "text": full,
                    "karakter": preferred_karakter,
                    "msg_id": stream_msg_id,
                },
                room=client_sid,
            )
        except Exception:
            pass

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                jawab_shiro_stream, text, preferred_karakter, True, on_token
            )
            result, status = future.result(timeout=45)
    except concurrent.futures.TimeoutError:
        logger.error("AI response timeout setelah 45 detik")
        socketio.emit("stream_end", {"text": "", "karakter": preferred_karakter}, room=client_sid)
        socketio.emit("error", {"message": "AI terlalu lama merespons"}, room=client_sid)
        return
    except Exception as e:
        logger.exception("AI processing error: %s", e)
        socketio.emit("stream_end", {"text": "", "karakter": preferred_karakter}, room=client_sid)
        socketio.emit("error", {"message": "Gagal memproses permintaan"}, room=client_sid)
        return

    reply = result.get("text", "Maaf, aku tidak mengerti.")
    suara_text = result.get("suara", reply)
    karakter = result.get("karakter", preferred_karakter)
    logger.info("AI reply (%s): %s", karakter, reply[:50])

    _emit_character_response(
        client_sid,
        reply,
        suara_text,
        karakter,
        stream_msg_id=stream_msg_id,
    )


@socketio.on("voice_text")
def handle_voice_text(data):
    """Handle teks dari browser SpeechRecognition (VTuber mode)."""
    global _processing_audio, _last_audio_time

    current_time = time.time()
    if current_time - _last_audio_time < 0.5:
        return
    _last_audio_time = current_time

    with _processing_lock:
        if _processing_audio:
            logger.debug("Masih memproses, abaikan voice_text")
            return
        _processing_audio = True

    client_sid = request.sid
    text = (data.get("text") or "").strip()
    karakter = (data.get("karakter") or "shiro").strip().lower()
    if karakter not in ("shiro", "sishin"):
        karakter = "shiro"
    voice_commands_enabled = data.get("voice_commands", True)
    if isinstance(voice_commands_enabled, str):
        voice_commands_enabled = voice_commands_enabled.lower() not in ("0", "false", "off", "no")
    else:
        voice_commands_enabled = bool(voice_commands_enabled)
    if not text:
        with _processing_lock:
            _processing_audio = False
        return

    def process_text():
        try:
            _process_voice_reply(
                text, client_sid, karakter, voice_commands_enabled=voice_commands_enabled
            )
        except Exception as e:
            logger.exception("Unexpected error in process_text: %s", e)
            try:
                socketio.emit("error", {"message": "Terjadi kesalahan internal"}, room=client_sid)
            except Exception:
                pass
        finally:
            with _processing_lock:
                global _processing_audio
                _processing_audio = False
            try:
                socketio.emit("audio_ready", {"status": "ready"}, room=client_sid)
            except Exception:
                pass

    threading.Thread(target=process_text, daemon=True).start()


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
    
    # Cegah proses bersamaan — abaikan tanpa error (client akan tunggu sinyal ready)
    with _processing_lock:
        if _processing_audio:
            logger.debug("Audio masih diproses, abaikan chunk baru")
            return
        _processing_audio = True
    
    # Tangkap sid client di thread utama
    client_sid = request.sid
    karakter = (data.get("karakter") or "shiro").strip().lower()
    if karakter not in ("shiro", "sishin"):
        karakter = "shiro"
    voice_commands_enabled = data.get("voice_commands", True)
    if isinstance(voice_commands_enabled, str):
        voice_commands_enabled = voice_commands_enabled.lower() not in ("0", "false", "off", "no")
    else:
        voice_commands_enabled = bool(voice_commands_enabled)
    
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
                try:
                    text = transcribe_audio_with_retry(audio_bytes)
                except Exception as e:
                    logger.exception("STT error: %s", e)
                    text = None

                if not text:
                    logger.warning("Transcription failed atau kosong")
                    socketio.emit("error", {
                        "message": "Tidak terdengar suara. Periksa mikrofon di Windows Settings > Sound > Input."
                    }, room=client_sid)
                    return

                _process_voice_reply(
                    text, client_sid, karakter, voice_commands_enabled=voice_commands_enabled
                )

            except Exception as e:
                logger.exception("Unexpected error in process_audio: %s", e)
                try:
                    socketio.emit("error", {"message": "Terjadi kesalahan internal"}, room=client_sid)
                except Exception:
                    pass
            finally:
                with _processing_lock:
                    global _processing_audio
                    _processing_audio = False
                try:
                    socketio.emit("audio_ready", {"status": "ready"}, room=client_sid)
                except Exception:
                    pass

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


def _emit_shutdown_and_exit():
    """Notify all clients to stop BGM/audio, then exit the server process."""
    try:
        with app.app_context():
            socketio.emit("app_shutdown", {"reason": "quit"}, namespace="/")
            socketio.sleep(0.6)
    except Exception as exc:
        logger.debug("app_shutdown emit: %s", exc)
    os._exit(0)


@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    """Local-only: stop audio on clients and shut down server (desktop tray quit)."""
    remote = (request.remote_addr or "").replace("::ffff:", "")
    if remote not in ("127.0.0.1", "::1"):
        return jsonify({"error": "forbidden"}), 403
    logger.info("Shutdown requested from %s", remote)
    threading.Thread(target=_emit_shutdown_and_exit, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/stop-audio", methods=["POST"])
def api_stop_audio():
    """Local-only: tell open browser tabs to stop BGM without killing server."""
    remote = (request.remote_addr or "").replace("::ffff:", "")
    if remote not in ("127.0.0.1", "::1"):
        return jsonify({"error": "forbidden"}), 403
    try:
        with app.app_context():
            socketio.emit("app_shutdown", {"reason": "stop_audio"}, namespace="/")
    except Exception as exc:
        logger.debug("stop-audio emit: %s", exc)
    return jsonify({"ok": True})


# ===== SHUTDOWN HANDLER =====
def signal_handler(sig, frame):
    logger.info("Shutting down gracefully...")
    try:
        socketio.emit("app_shutdown", {"reason": "signal"}, namespace="/")
    except Exception:
        pass
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

    # Preload Whisper agar STT pertama tidak lambat
    logger.info("Preloading Whisper model...")
    get_whisper_model()

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
    except OSError as e:
        winerr = getattr(e, "winerror", None)
        if winerr == 10048 or e.errno in (48, 98, 10048):
            logger.error("Port %s sudah dipakai — jalankan start.bat untuk restart otomatis", config.FLASK_PORT)
            print()
            print("=" * 50)
            print("  PORT %s SUDAH DIPAKAI" % config.FLASK_PORT)
            print("=" * 50)
            print("  Cara paling mudah:")
            print("    Double-click  start.bat")
            print("  Atau tutup terminal lama (Ctrl+C) lalu coba lagi.")
            print("=" * 50)
            print()
        else:
            logger.exception("Server error: %s", e)
    except Exception as e:
        logger.exception("Server error: %s", e)
    finally:
        logger.info("Server shutdown complete")