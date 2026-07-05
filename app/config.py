"""
eCast — Configuration Module
Loads environment variables and provides system-wide constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Directory Paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / os.getenv("UPLOAD_DIR", "./uploads/")
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "./outputs/")
MODEL_CACHE_DIR = BASE_DIR / os.getenv("MODEL_CACHE_DIR", "./models/")

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# File Upload
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

# Translation Settings
BATCH_SIZE_TRANSLATION: int = int(os.getenv("BATCH_SIZE_TRANSLATION", "8"))
MAX_INPUT_TOKENS: int = int(os.getenv("MAX_INPUT_TOKENS", "512"))
NUM_BEAMS: int = int(os.getenv("NUM_BEAMS", "4"))

# Model identifiers
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")


# TTS Settings
TTS_SPEED: float = float(os.getenv("TTS_SPEED", "0.9"))
TTS_SAMPLE_RATE: int = int(os.getenv("TTS_SAMPLE_RATE", "22050"))
PODCAST_SILENCE_MS: int = int(os.getenv("PODCAST_SILENCE_MS", "500"))

# Edge-TTS voice mapping
EDGE_TTS_VOICES = {
    "ar": "ar-SA-HamedNeural",       # Arabic (Saudi Arabia) male
    "id": "id-ID-ArdiNeural",        # Indonesian male
    "en": "en-US-GuyNeural",         # English (US) male
}

# Processing
CHAPTER_LIMIT: int = int(os.getenv("CHAPTER_LIMIT", "3"))
OUTPUT_FORMAT: str = os.getenv("OUTPUT_FORMAT", "mp3")

# Device Detection (CPU / GPU)
DEVICE = os.getenv("DEVICE", "cuda") # Assuming CUDA for llama.cpp by default, but it will fallback to CPU if no GPU


# Server
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))

# Supported MIME Types
ALLOWED_MIME_TYPES = [
    "application/epub+zip",
    "application/octet-stream",  # Fallback for some systems
]
ALLOWED_EXTENSIONS = [".epub"]

# FFmpeg Configuration (Manual Installation)
_manual_ffmpeg_dir = r"C:\ffmpeg\bin"
if os.path.exists(_manual_ffmpeg_dir):
    FFMPEG_PATH = os.path.join(_manual_ffmpeg_dir, "ffmpeg.exe")
    FFPROBE_PATH = os.path.join(_manual_ffmpeg_dir, "ffprobe.exe")
    if _manual_ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _manual_ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
else:
    # Fallback if manual installation is not found
    try:
        import imageio_ffmpeg
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
        FFPROBE_PATH = "ffprobe" # imageio-ffmpeg doesn't bundle ffprobe
        _ffmpeg_dir = str(Path(FFMPEG_PATH).parent)
        if _ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    except ImportError:
        FFMPEG_PATH = "ffmpeg"
        FFPROBE_PATH = "ffprobe"



def get_config_summary() -> dict:
    """Return a summary of current configuration for debugging."""
    return {
        "device": DEVICE,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "batch_size": BATCH_SIZE_TRANSLATION,
        "tts_speed": TTS_SPEED,
        "chapter_limit": CHAPTER_LIMIT,
        "output_format": OUTPUT_FORMAT,
        "upload_dir": str(UPLOAD_DIR),
        "output_dir": str(OUTPUT_DIR),
        "model_cache_dir": str(MODEL_CACHE_DIR),
    }
