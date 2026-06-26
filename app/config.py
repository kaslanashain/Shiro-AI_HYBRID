import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://localhost:50021")

FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))

MAX_CACHE = int(os.environ.get("MAX_CACHE", "100"))
MAX_TTS_FILES = int(os.environ.get("MAX_TTS_FILES", "50"))
TTS_FILE_AGE_LIMIT = int(os.environ.get("TTS_FILE_AGE_LIMIT", "3600"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))

TEMP_DIR = os.path.join(BASE_DIR, "tmp")
DB_PATH = os.path.join(BASE_DIR, "Shiro_Sishin.db")

OLLAMA_OPTIONS = {
    "temperature": 0.1,
    "top_p": 0.9,
    "top_k": 40,
    "num_predict": 128,
    "repeat_penalty": 1.1,
}

SHIRO_KEYWORDS = ("shiro", "shiro-chan", "shirochan", "siro")
SISHIN_KEYWORDS = ("sishin", "sashin", "sisin", "shishin")
POSITIVE_KEYWORDS = ("sayang", "imut", "cantik", "cinta", "suka", "love", "daisuki")
NEGATIVE_KEYWORDS = ("benci", "jelek", "bodoh", "jahat", "baka")
FACT_KEYWORDS = ("ingat ya", "jangan lupa", "remember", "catat")
