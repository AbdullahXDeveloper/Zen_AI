"""
app/ai/claude_client.py
Zen AI — Universal AI Client  v2

Supports 5 providers selectable from Settings:
  - ollama      local Ollama server (default)
  - openai      OpenAI API (GPT-4o, GPT-4, GPT-3.5)
  - gemini      Google Gemini (via REST API)
  - anthropic   Anthropic Claude (via REST API)
  - custom      Any OpenAI-compatible API

Usage (unchanged across the codebase):
    from app.ai.claude_client import get_client
    client = get_client()
    text   = client.ask(prompt, system="...")
    data   = client.ask_json(prompt, system="...")

Switching provider at runtime:
    from app.ai.claude_client import rebuild_client
    rebuild_client()   # re-reads config/user_settings.json
"""

from __future__ import annotations
import json
import re
import requests

# ── JSON extraction helper ─────────────────────────────────
def _extract_json(text: str) -> str:
    """Strip markdown fences and extract JSON substring."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


# ══════════════════════════════════════════════════════════
# BASE
# ══════════════════════════════════════════════════════════
class BaseAIClient:
    """Interface contract — all providers implement ask() and ask_json()."""

    def ask(self, prompt: str, system: str = "",
            system_prompt: str = "", temperature: float = 0.7) -> str:
        raise NotImplementedError

    def ask_json(self, prompt: str, system: str = "",
                 system_prompt: str = "", temperature: float = 0.7,
                 max_tokens: int = 2048) -> dict | list:
        raise NotImplementedError

    @staticmethod
    def _parse_json(text: str) -> dict | list:
        try:
            return json.loads(_extract_json(text))
        except json.JSONDecodeError as e:
            print(f"[AI] Invalid JSON: {e}\nRaw: {text[:300]}")
            return {}


# ══════════════════════════════════════════════════════════
# PROVIDER 1 — OLLAMA  (local)
# ══════════════════════════════════════════════════════════
class OllamaClient(BaseAIClient):
    def __init__(self, model: str = "qwen2.5:7b",
                 base_url: str = "http://localhost:11434"):
        self.model    = model
        self.base_url = base_url.rstrip("/")

    def ask(self, prompt: str, system: str = "",
            system_prompt: str = "", temperature: float = 0.7) -> str:
        sys_text = system or system_prompt or ""
        payload  = {
            "model":   self.model,
            "prompt":  prompt,
            "stream":  False,
            "options": {"temperature": temperature},
        }
        if sys_text:
            payload["system"] = sys_text
        try:
            r = requests.post(f"{self.base_url}/api/generate",
                              json=payload, timeout=120)
            r.raise_for_status()
            return r.json().get("response", "")
        except requests.ConnectionError:
            return "[Ollama offline — 'ollama serve' chalao]"
        except requests.Timeout:
            return "[Error: Ollama timeout (120s)]"
        except Exception as e:
            return f"[Ollama Error: {e}]"

    def ask_json(self, prompt: str, system: str = "",
                 system_prompt: str = "", temperature: float = 0.7,
                 max_tokens: int = 2048) -> dict | list:
        sys_text = system or system_prompt or ""
        payload  = {
            "model":   self.model,
            "prompt":  prompt,
            "stream":  False,
            "format":  "json",
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if sys_text:
            payload["system"] = sys_text
        try:
            r = requests.post(f"{self.base_url}/api/generate",
                              json=payload, timeout=180)
            r.raise_for_status()
            raw = r.json().get("response", "")
            return self._parse_json(raw)
        except requests.ConnectionError:
            print("[Ollama] offline")
            return {}
        except requests.Timeout:
            print("[Ollama] JSON timeout (180s)")
            return {}
        except Exception as e:
            print(f"[Ollama JSON Error] {e}")
            return {}


# ══════════════════════════════════════════════════════════
# PROVIDER 2 — OPENAI
# ══════════════════════════════════════════════════════════
class OpenAIClient(BaseAIClient):
    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model   = model

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

    def _build_messages(self, prompt: str, sys_text: str) -> list:
        msgs = []
        if sys_text:
            msgs.append({"role": "system", "content": sys_text})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def ask(self, prompt: str, system: str = "",
            system_prompt: str = "", temperature: float = 0.7) -> str:
        sys_text = system or system_prompt or ""
        payload  = {
            "model":       self.model,
            "messages":    self._build_messages(prompt, sys_text),
            "temperature": temperature,
        }
        try:
            r = requests.post(self.API_URL, headers=self._headers(),
                              json=payload, timeout=120)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[OpenAI Error: {e}]"

    def ask_json(self, prompt: str, system: str = "",
                 system_prompt: str = "", temperature: float = 0.7,
                 max_tokens: int = 2048) -> dict | list:
        sys_text = system or system_prompt or ""
        json_inst = "\n\nReturn ONLY valid JSON, no markdown fences."
        payload   = {
            "model":        self.model,
            "messages":     self._build_messages(prompt + json_inst, sys_text),
            "temperature":  temperature,
            "max_tokens":   max_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            r = requests.post(self.API_URL, headers=self._headers(),
                              json=payload, timeout=180)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
            return self._parse_json(raw)
        except Exception as e:
            print(f"[OpenAI JSON Error] {e}")
            return {}


# ══════════════════════════════════════════════════════════
# PROVIDER 3 — GOOGLE GEMINI  (REST API)
# ══════════════════════════════════════════════════════════
class GeminiClient(BaseAIClient):
    BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model   = model

    def _url(self, method: str = "generateContent") -> str:
        return f"{self.BASE}/{self.model}:{method}?key={self.api_key}"

    def _build_body(self, prompt: str, sys_text: str,
                    temperature: float, max_tokens: int = 2048) -> dict:
        body: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if sys_text:
            body["systemInstruction"] = {"parts": [{"text": sys_text}]}
        return body

    def ask(self, prompt: str, system: str = "",
            system_prompt: str = "", temperature: float = 0.7) -> str:
        sys_text = system or system_prompt or ""
        try:
            r = requests.post(self._url(), timeout=120,
                              json=self._build_body(prompt, sys_text, temperature))
            r.raise_for_status()
            parts = r.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except Exception as e:
            return f"[Gemini Error: {e}]"

    def ask_json(self, prompt: str, system: str = "",
                 system_prompt: str = "", temperature: float = 0.7,
                 max_tokens: int = 2048) -> dict | list:
        sys_text = system or system_prompt or ""
        json_prompt = prompt + "\n\nReturn ONLY valid JSON, no markdown."
        try:
            body = self._build_body(json_prompt, sys_text, temperature, max_tokens)
            body["generationConfig"]["responseMimeType"] = "application/json"
            r = requests.post(self._url(), timeout=180, json=body)
            r.raise_for_status()
            parts = r.json()["candidates"][0]["content"]["parts"]
            raw   = "".join(p.get("text", "") for p in parts)
            return self._parse_json(raw)
        except Exception as e:
            print(f"[Gemini JSON Error] {e}")
            return {}


# ══════════════════════════════════════════════════════════
# PROVIDER 4 — ANTHROPIC CLAUDE
# ══════════════════════════════════════════════════════════
class AnthropicClient(BaseAIClient):
    API_URL = "https://api.anthropic.com/v1/messages"
    VERSION = "2023-06-01"

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model   = model

    def _headers(self) -> dict:
        return {
            "x-api-key":         self.api_key,
            "anthropic-version": self.VERSION,
            "Content-Type":      "application/json",
        }

    def _call(self, prompt: str, sys_text: str,
              temperature: float, max_tokens: int) -> str:
        payload: dict = {
            "model":      self.model,
            "max_tokens": max_tokens,
            "messages":   [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if sys_text:
            payload["system"] = sys_text
        r = requests.post(self.API_URL, headers=self._headers(),
                          json=payload, timeout=180)
        r.raise_for_status()
        return r.json()["content"][0]["text"]

    def ask(self, prompt: str, system: str = "",
            system_prompt: str = "", temperature: float = 0.7) -> str:
        sys_text = system or system_prompt or ""
        try:
            return self._call(prompt, sys_text, temperature, 4096)
        except Exception as e:
            return f"[Anthropic Error: {e}]"

    def ask_json(self, prompt: str, system: str = "",
                 system_prompt: str = "", temperature: float = 0.7,
                 max_tokens: int = 2048) -> dict | list:
        sys_text = system or system_prompt or ""
        json_prompt = prompt + "\n\nReturn ONLY a valid JSON object, no markdown."
        try:
            raw = self._call(json_prompt, sys_text, temperature, max_tokens)
            return self._parse_json(raw)
        except Exception as e:
            print(f"[Anthropic JSON Error] {e}")
            return {}


# ══════════════════════════════════════════════════════════
# PROVIDER 5 — CUSTOM  (OpenAI-compatible)
# ══════════════════════════════════════════════════════════
class CustomAPIClient(OpenAIClient):
    """OpenAI-compatible endpoint with custom base URL."""

    def __init__(self, api_key: str, model: str, base_url: str):
        super().__init__(api_key, model)
        self.API_URL = base_url.rstrip("/") + "/chat/completions"

    def ask_json(self, prompt: str, system: str = "",
                 system_prompt: str = "", temperature: float = 0.7,
                 max_tokens: int = 2048) -> dict | list:
        # Custom APIs may not support response_format — use plain ask + parse
        sys_text    = system or system_prompt or ""
        json_prompt = prompt + "\n\nReturn ONLY valid JSON, no markdown."
        payload = {
            "model":       self.model,
            "messages":    self._build_messages(json_prompt, sys_text),
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        try:
            r = requests.post(self.API_URL, headers=self._headers(),
                              json=payload, timeout=180)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
            return self._parse_json(raw)
        except Exception as e:
            print(f"[Custom API JSON Error] {e}")
            return {}


# ══════════════════════════════════════════════════════════
# FACTORY — build client from settings
# ══════════════════════════════════════════════════════════
def _build_client() -> BaseAIClient:
    """Read config/user_settings.json and instantiate the right client."""
    try:
        from config.app_settings import get_app_settings
        s = get_app_settings()
        provider = s.ai_provider
        model    = s.ai_model
        key      = s.api_key
        url      = s.ollama_url
        temp     = s.temperature
    except Exception:
        # Fallback to Ollama if settings unavailable
        return OllamaClient()

    if provider == "openai":
        return OpenAIClient(api_key=key, model=model)
    elif provider == "gemini":
        return GeminiClient(api_key=key, model=model)
    elif provider == "anthropic":
        return AnthropicClient(api_key=key, model=model)
    elif provider == "custom":
        return CustomAPIClient(api_key=key, model=model, base_url=url)
    else:  # ollama (default)
        return OllamaClient(model=model, base_url=url)


# ══════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════
_client: BaseAIClient | None = None


def get_client() -> BaseAIClient:
    """Return the singleton AI client (auto-builds on first call)."""
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def rebuild_client() -> BaseAIClient:
    """Force rebuild from current settings — call after Settings save."""
    global _client
    _client = _build_client()
    print(f"[AI] Client rebuilt: {type(_client).__name__} / {getattr(_client, 'model', '?')}")
    return _client


# ── Legacy alias for any code that imported LocalOllamaClient directly ───────
LocalOllamaClient = OllamaClient
