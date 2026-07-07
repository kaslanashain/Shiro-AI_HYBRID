import os
from dotenv import load_dotenv

os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_VISION_MODEL = os.environ.get("GEMINI_VISION_MODEL", "gemini-1.5-flash")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_VISION_MODEL = os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini")
# ===== TAMBAHAN UNTUK GROQ =====
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://localhost:50021")

FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))
SECRET_KEY = os.environ.get("SECRET_KEY", "shiro-dev-change-in-production")
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in ("1", "true", "yes")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

MAX_CACHE = int(os.environ.get("MAX_CACHE", "100"))
MAX_TTS_FILES = int(os.environ.get("MAX_TTS_FILES", "50"))
TTS_FILE_AGE_LIMIT = int(os.environ.get("TTS_FILE_AGE_LIMIT", "3600"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
MAX_VIDEO_UPLOAD_BYTES = int(os.environ.get("MAX_VIDEO_UPLOAD_BYTES", str(20 * 1024 * 1024)))
VIDEO_KEYFRAME_COUNT = int(os.environ.get("VIDEO_KEYFRAME_COUNT", "4"))
VIDEO_UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads", "videos")

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

ROMAJI_KEYWORDS = (
    "konnichiwa", "ohayou", "ohayo", "konbanwa", "arigatou", "arigato", "gomen",
    "gomennasai", "daisuki", "suki", "sayonara", "onii-chan", "onee-san", "onii",
    "onee", "genki", "kawaii", "sugoi", "yatta", "itadakimasu", "gochisousama",
    "kowai", "tanoshii", "ureshii", "itai", "hontou", "maji", "baka", "nya",
    "neko", "desu", "masu", "chan", "san", "kun", "senpai", "kouhai", "matte",
    "chotto", "doko", "nani", "doushite", "yokatta", "minna", "tomodachi",
    "gambatte", "yoroshiku", "ittekimasu", "tadaima", "okaeri", "oyasumi",
)


# =============================================
# TAMBAHAN: Verifikasi dan Logging (Opsional)
# =============================================
import logging
logger = logging.getLogger(__name__)

# Pastikan OLLAMA_HOST terbaca
logger.info("[OK] OLLAMA_HOST = %s", os.environ.get("OLLAMA_HOST", "TIDAK SET"))
logger.info("[OK] OLLAMA_MODEL = %s", OLLAMA_MODEL)
logger.info("[OK] VOICEVOX_URL = %s", VOICEVOX_URL)