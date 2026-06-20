
import json
import requests


class LocalOllamaClient:
    """
    Ollama API client — wraps qwen2.5:7b (or any local model).

    Both ask() and ask_json() accept the same keyword args as the
    Anthropic/OpenAI clients so that lore_generator, story_writer, etc.
    can call them without worrying which backend is active.
    """

    def __init__(self, model="qwen2.5:7b"):
        self.api_url = "http://localhost:11434/api/generate"
        self.model = model

    # ─────────────────────────────────────────────────────────
    # ask() — free-form text response
    # ─────────────────────────────────────────────────────────
    def ask(self, prompt: str, system_prompt: str = None,
            system: str = None, temperature: float = 0.7) -> str:
        """
        Standard text generation.

        Accepts both `system_prompt` (old kwarg used by ai_chat_view)
        and `system` (new kwarg used by lore_generator / story_writer)
        so both callers work without modification.
        """
        # Unify system prompt kwarg names
        sys_text = system or system_prompt or ""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if sys_text:
            payload["system"] = sys_text   # Ollama native system field

        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.ConnectionError:
            print(
                "[Error] Ollama chal nahi raha. "
                "Terminal mein 'ollama serve' ya 'ollama run qwen2.5:7b' chalayein."
            )
            return "Local AI is offline."
        except requests.exceptions.Timeout:
            print("[Error] Ollama response timeout (120s).")
            return "Error: AI response timeout."
        except Exception as e:
            print(f"[Ollama Error] {e}")
            return f"Error: {str(e)}"

    # ─────────────────────────────────────────────────────────
    # ask_json() — structured JSON response
    # ─────────────────────────────────────────────────────────
    def ask_json(self, prompt: str, system_prompt: str = None,
                 system: str = None, temperature: float = 0.7,
                 max_tokens: int = 2048) -> dict | list:
        """
        Structured JSON data generation (lore extraction, generators).

        Returns a dict or list on success, or {} on failure.
        Accepts both `system_prompt` and `system` kwarg names.
        """
        sys_text = system or system_prompt or ""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",   # Ollama strict JSON mode
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if sys_text:
            payload["system"] = sys_text

        try:
            response = requests.post(self.api_url, json=payload, timeout=180)
            response.raise_for_status()
            text_response = response.json().get("response", "").strip()

            # Agar Qwen phir bhi markdown code blocks bhej de, saaf karein
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.startswith("```"):
                text_response = text_response[3:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]

            return json.loads(text_response.strip())

        except json.JSONDecodeError as e:
            print(f"[Error] Model ne invalid JSON return kiya: {e}")
            return {}
        except requests.exceptions.ConnectionError:
            print("[Error] Ollama offline hai.")
            return {}
        except requests.exceptions.Timeout:
            print("[Error] Ollama JSON response timeout (180s).")
            return {}
        except Exception as e:
            print(f"[Ollama JSON Error] {e}")
            return {}


# ─────────────────────────────────────────────────────────────
# Singleton — project mein har jagah ek hi instance use ho
# ─────────────────────────────────────────────────────────────
_client = None


def get_client() -> LocalOllamaClient:
    global _client
    if _client is None:
        _client = LocalOllamaClient(model="qwen2.5:7b")
    return _client
