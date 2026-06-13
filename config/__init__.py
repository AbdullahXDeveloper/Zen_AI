"""
config package
Loads environment variables from config/.env and exposes them as constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Path to config/.env regardless of where the app is launched from
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))

# Project root (ZenAI/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "zenai.db"
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
LORE_DIR = PROJECT_ROOT / "data" / "lore"
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"


def validate_api_key() -> bool:
    """Returns True if a non-placeholder API key is set."""
    return bool(ANTHROPIC_API_KEY) and "PASTE_YOUR" not in ANTHROPIC_API_KEY
