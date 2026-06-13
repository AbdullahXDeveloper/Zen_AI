"""
app/ai/claude_client.py

Thin wrapper around the Anthropic API:
- Handles client init, retries on transient errors
- Provides plain-text and structured-JSON completion helpers
- All other ai/ modules should call through this, never call anthropic directly
"""
import json
import time
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS, validate_api_key


class ClaudeClientError(Exception):
    pass


class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 max_tokens: Optional[int] = None, max_retries: int = 3):
        key = api_key or ANTHROPIC_API_KEY
        if not key or "PASTE_YOUR" in key:
            raise ClaudeClientError(
                "ANTHROPIC_API_KEY not set. Edit config/.env and add your real key."
            )
        self.client = anthropic.Anthropic(api_key=key)
        self.model = model or CLAUDE_MODEL
        self.max_tokens = max_tokens or CLAUDE_MAX_TOKENS
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # Core call with retry/backoff
    # ------------------------------------------------------------------
    def _call(self, messages: list[dict], system: Optional[str] = None,
              max_tokens: Optional[int] = None, temperature: float = 1.0) -> str:
        last_err = None
        for attempt in range(self.max_retries):
            try:
                kwargs = dict(
                    model=self.model,
                    max_tokens=max_tokens or self.max_tokens,
                    temperature=temperature,
                    messages=messages,
                )
                if system:
                    kwargs["system"] = system

                response = self.client.messages.create(**kwargs)

                # Concatenate all text blocks
                text_parts = [
                    block.text for block in response.content
                    if getattr(block, "type", None) == "text"
                ]
                return "\n".join(text_parts)

            except (anthropic.APIConnectionError, anthropic.RateLimitError,
                    anthropic.InternalServerError) as e:
                last_err = e
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            except anthropic.APIStatusError as e:
                # Non-retryable (bad request, auth, etc.)
                raise ClaudeClientError(f"Claude API error ({e.status_code}): {e.message}")

        raise ClaudeClientError(f"Claude API failed after {self.max_retries} retries: {last_err}")

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def ask(self, prompt: str, system: Optional[str] = None,
            max_tokens: Optional[int] = None, temperature: float = 1.0) -> str:
        """Plain text completion. Returns raw string response."""
        messages = [{"role": "user", "content": prompt}]
        return self._call(messages, system=system, max_tokens=max_tokens, temperature=temperature)

    def ask_json(self, prompt: str, system: Optional[str] = None,
                  max_tokens: Optional[int] = None, temperature: float = 0.7) -> dict | list:
        """
        Completion that expects a JSON response.
        Appends an instruction to return JSON only, strips markdown fences,
        and parses the result. Raises ClaudeClientError on parse failure.
        """
        json_instruction = (
            "\n\nIMPORTANT: Respond with ONLY valid JSON. "
            "No preamble, no explanation, no markdown code fences."
        )
        full_prompt = prompt + json_instruction

        raw = self.ask(full_prompt, system=system, max_tokens=max_tokens, temperature=temperature)
        cleaned = self._strip_json_fences(raw)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ClaudeClientError(
                f"Failed to parse JSON from Claude response: {e}\nRaw response:\n{raw}"
            )

    @staticmethod
    def _strip_json_fences(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            # Remove first line (```json or ```) and trailing ```
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text


# Module-level singleton, lazily initialized
_client: Optional[ClaudeClient] = None


def get_client() -> ClaudeClient:
    global _client
    if _client is None:
        _client = ClaudeClient()
    return _client


def is_configured() -> bool:
    return validate_api_key()
