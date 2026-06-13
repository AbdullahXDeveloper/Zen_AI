"""Application settings and environment helpers."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "zenai.db"

load_dotenv(BASE_DIR / ".env", override=False)


def get_setting(name: str, default: str | None = None) -> str | None:
    """Read a setting from environment variables."""
    return os.getenv(name, default)


APP_NAME = "ZenAI"
ANTHROPIC_API_KEY = get_setting("ANTHROPIC_API_KEY")
DEFAULT_MODEL = get_setting("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
