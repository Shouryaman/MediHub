import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data"
DB_FAISS_PATH = BASE_DIR / "vectorstore" / "db_faiss"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_VISION_MODEL = os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini")
OPENAI_STT_MODEL = os.environ.get("OPENAI_STT_MODEL", "whisper-1")
OPENAI_TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "tts-1")
OPENAI_TTS_VOICE = os.environ.get("OPENAI_TTS_VOICE", "alloy")
# API embeddings — no local torch (critical for Render memory limits)
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
RETRIEVER_K = int(os.environ.get("RETRIEVER_K", "4"))
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "50"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
VISION_MAX_SIDE = int(os.environ.get("VISION_MAX_SIDE", "1280"))
TEMP_DIR = BASE_DIR / "tmp"
TEMP_DIR.mkdir(exist_ok=True)


def require_openai_key() -> str:
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add it to your .env file before starting the app."
        )
    return OPENAI_API_KEY
