"""
config/app_settings.py
Zen AI — Persistent Application Settings Manager

Stores and retrieves user settings from config/user_settings.json.
Provides a global singleton: get_app_settings()

Schema:
{
  "ai": {
    "provider":    "groq",            # groq | ollama | openai | gemini | anthropic | custom
    "model":       "llama-3.1-8b-instant",
    "ollama_url":  "http://localhost:11434",
    "api_key":     "",                # stored as plain text (local only)
    "temperature": 1.0
  },
  "display": {
    "width":  1280,
    "height": 800
  },
  "worldbuilding": {
    "default_universe_id": null,
    "default_canon":       "canon",
    "default_score":       50
  },
  "search": {
    "max_results":      25,
    "semantic_enabled": true
  }
}
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

_SETTINGS_PATH = Path(__file__).resolve().parent / "user_settings.json"

_DEFAULTS: dict = {
    "ai": {
        "provider":   "groq",
        "model":      "llama-3.1-8b-instant",
        "ollama_url": "http://localhost:11434",
        "api_key":    "",
        "temperature": 1.0,
    },
    "display": {
        "width":  1280,
        "height": 800,
    },
    "worldbuilding": {
        "default_universe_id": None,
        "default_canon":       "canon",
        "default_score":       50,
    },
    "search": {
        "max_results":      25,
        "semantic_enabled": True,
    },
}


class AppSettings:
    """Singleton settings manager — load/save JSON."""

    def __init__(self):
        self._data: dict = {}
        self.load()

    # ── IO ────────────────────────────────────────────────

    def load(self):
        """Load from disk; merge missing keys from defaults."""
        if _SETTINGS_PATH.exists():
            try:
                with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Deep merge: loaded overrides defaults
                self._data = self._deep_merge(_DEFAULTS, loaded)
            except Exception as e:
                print(f"[Settings] Could not load {_SETTINGS_PATH}: {e}")
                self._data = json.loads(json.dumps(_DEFAULTS))
        else:
            self._data = json.loads(json.dumps(_DEFAULTS))

    def save(self):
        """Persist current settings to disk."""
        try:
            _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Settings] Could not save settings: {e}")

    # ── Accessors ─────────────────────────────────────────

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self._data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any):
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value

    def get_section(self, section: str) -> dict:
        return dict(self._data.get(section, {}))

    def update_section(self, section: str, values: dict):
        if section not in self._data:
            self._data[section] = {}
        self._data[section].update(values)

    # ── Convenience ───────────────────────────────────────

    @property
    def ai_provider(self) -> str:
        return self.get("ai", "provider", "groq")

    @property
    def ai_model(self) -> str:
        return self.get("ai", "model", "llama-3.1-8b-instant")

    @property
    def ollama_url(self) -> str:
        return self.get("ai", "ollama_url", "http://localhost:11434")

    @property
    def api_key(self) -> str:
        return self.get("ai", "api_key", "")

    @property
    def temperature(self) -> float:
        return float(self.get("ai", "temperature", 1.0))

    @property
    def display_size(self) -> tuple[int, int]:
        return (
            int(self.get("display", "width", 1280)),
            int(self.get("display", "height", 800)),
        )

    # ── Helpers ───────────────────────────────────────────

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = json.loads(json.dumps(base))
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = AppSettings._deep_merge(result[k], v)
            else:
                result[k] = v
        return result


# ── Singleton ─────────────────────────────────────────────
_instance: AppSettings | None = None


def get_app_settings() -> AppSettings:
    global _instance
    if _instance is None:
        _instance = AppSettings()
    return _instance


def reload_settings():
    """Force reload from disk (call after external edits)."""
    global _instance
    _instance = AppSettings()
    return _instance
