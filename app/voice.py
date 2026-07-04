import os
import logging
import tempfile
import io
import time
import subprocess
import glob

# ===== SET FFMPEG PATH =====
FFMPEG_PATH = r"D:\ffmpeg\bin\ffmpeg.exe"
FFMPEG_DIR = os.path.dirname(FFMPEG_PATH)
os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

import whisper
import soundfile as sf

logger = logging.getLogger(__name__)

if os.path.exists(FFMPEG_PATH):
    logger.info(f"FFmpeg ditemukan di: {FFMPEG_PATH}")
else:
    logger.warning(f"FFmpeg TIDAK ditemukan di {FFMPEG_PATH}")

# ===== KONFIGURASI DEBUG AUDIO =====
DEBUG_AUDIO_DIR = "debug_audio"          # Folder untuk menyimpan file debug
MAX_DEBUG_FILES = 10                     # Maksimal file yang disimpan

# Buat folder debug jika belum ada
os.makedirs(DEBUG_AUDIO_DIR, exist_ok=True)

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        logger.info("Loading Whisper model (base)...")
        try:
            _whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error("Gagal load Whisper model: %s", e)
            _whisper_model = False
    return _whisper_model if _whisper_model is not False else None


def convert_audio_to_wav_ffmpeg(audio_bytes: bytes) -> bytes:
    """Konversi audio ke WAV 16kHz mono menggunakan ffmpeg."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as fin:
            fin.write(audio_bytes)
            input_path = fin.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fout:
            output_path = fout.name

        cmd = [
            FFMPEG_PATH,
            "-i", input_path,
            "-ac", "1",
            "-ar", "16000",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-y",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=10, check=True)

        with open(output_path, "rb") as f:
            wav_bytes = f.read()

        try:
            os.unlink(input_path)
            os.unlink(output_path)
        except:
            pass

        return wav_bytes

    except Exception as e:
        logger.warning(f"ffmpeg conversion error: {e}")
        return None


def cleanup_debug_audio():
    """Hapus file debug audio lama jika melebihi batas maksimum."""
    try:
        # Cari semua file .webm di folder debug
        files = glob.glob(os.path.join(DEBUG_AUDIO_DIR, "*.webm"))
        if len(files) <= MAX_DEBUG_FILES:
            return
        
        # Urutkan berdasarkan waktu modifikasi (terlama dulu)
        files.sort(key=os.path.getmtime)
        
        # Hapus file yang melebihi batas
        for f in files[:-MAX_DEBUG_FILES]:
            try:
                os.remove(f)
                logger.debug(f"Removed old debug audio: {f}")
            except Exception as e:
                logger.warning(f"Gagal hapus {f}: {e}")
    except Exception as e:
        logger.warning(f"Cleanup debug audio error: {e}")


def _is_silent_wav(wav_path: str, threshold_db: float = -38.0) -> bool:
    """Cek apakah WAV hampir sunyi (mic tidak menangkap suara)."""
    try:
        cmd = [FFMPEG_PATH, "-i", wav_path, "-af", "volumedetect", "-f", "null", "-"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        for line in result.stderr.splitlines():
            if "mean_volume" in line:
                db = float(line.split("mean_volume:")[1].split("dB")[0].strip())
                logger.info(f"Volume audio: {db:.1f} dB")
                return db < threshold_db
    except Exception as e:
        logger.warning(f"Volume check error: {e}")
    return False


def transcribe_audio(audio_bytes: bytes) -> str:
    if not audio_bytes or len(audio_bytes) < 100:
        logger.warning("Audio terlalu pendek")
        return None

    # Simpan raw audio untuk debug (hanya jika diizinkan)
    # Jika ingin menonaktifkan debug, hapus atau komentari blok ini
    try:
        timestamp = int(time.time())
        debug_path = os.path.join(DEBUG_AUDIO_DIR, f"debug_audio_raw_{timestamp}.webm")
        with open(debug_path, "wb") as f:
            f.write(audio_bytes)
        logger.info(f"Raw audio saved: {debug_path} ({len(audio_bytes)} bytes)")
        # Panggil cleanup setelah menyimpan
        cleanup_debug_audio()
    except Exception as e:
        logger.warning(f"Gagal simpan debug audio: {e}")

    # Konversi ke WAV
    wav_bytes = convert_audio_to_wav_ffmpeg(audio_bytes)
    if wav_bytes is None or len(wav_bytes) < 1000:
        logger.warning("Konversi WAV gagal, coba pakai pydub fallback")
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            audio = audio.set_channels(1).set_frame_rate(16000)
            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            wav_bytes = wav_io.read()
        except Exception as e:
            logger.warning(f"Fallback pydub gagal: {e}")
            return None

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name
        logger.info(f"WAV saved: {tmp_path} ({os.path.getsize(tmp_path)} bytes)")

        if _is_silent_wav(tmp_path):
            logger.warning("Audio sunyi — mic tidak menangkap suara")
            return None

        # === PRIORITAS: Whisper (lokal, tanpa timeout jaringan) ===
        model = get_whisper_model()
        if model:
            try:
                start = time.time()
                result = model.transcribe(
                    tmp_path,
                    language="id",
                    fp16=False,
                    condition_on_previous_text=False,
                )
                elapsed = (time.time() - start) * 1000
                text = result.get("text", "").strip()
                if text:
                    logger.info(f"Whisper berhasil ({int(elapsed)}ms): {text[:50]}")
                    return text
                logger.warning("Whisper menghasilkan teks kosong")
            except Exception as e:
                logger.warning(f"Whisper error: {e}")

        # === Fallback: Google Speech Recognition ===
        logger.info("Mencoba Google Speech Recognition (online)...")
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.AudioFile(tmp_path) as source:
                audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="id-ID")
            if text:
                logger.info(f"Google STT berhasil: {text[:50]}")
                return text
        except ImportError:
            logger.warning("SpeechRecognition tidak terinstal. Install: pip install SpeechRecognition")
        except sr.UnknownValueError:
            logger.warning("Google STT tidak bisa mengenali suara (mungkin terlalu pelan atau sunyi)")
        except sr.RequestError as e:
            logger.warning(f"Google STT request error: {e}")
        except Exception as e:
            logger.warning(f"Google STT error: {e}")

        return None

    except Exception as e:
        logger.exception(f"STT error: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass


def transcribe_audio_with_retry(audio_bytes: bytes, max_retries=2) -> str:
    for attempt in range(max_retries + 1):
        result = transcribe_audio(audio_bytes)
        if result:
            return result
        if attempt < max_retries:
            logger.info(f"Retry STT {attempt+1}/{max_retries}")
            time.sleep(0.5)
    return None