
import json
import requests

class LocalOllamaClient:
    def __init__(self, model="qwen2.5:7b"):
        
        self.api_url = "http://localhost:11434/api/generate"
        self.model = model

    def ask(self, prompt, system_prompt=None):
        """Standard text generation ke liye"""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.ConnectionError:
            print("[Error] Ollama background mein run nahi ho raha. Terminal mein 'ollama serve' ya 'ollama run qwen2.5:7b' chalayein.")
            return "Local AI is offline."
        except Exception as e:
            print(f"[Ollama Error] {e}")
            return f"Error: {str(e)}"

    def ask_json(self, prompt, system_prompt=None):
        """Structured JSON data generation ke liye (Lore extraction, generators)"""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
            
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "format": "json"  # Ollama ka strict JSON mode
        }
        
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            text_response = response.json().get("response", "").strip()
            
            # Agar Qwen phir bhi markdown code blocks bhej de, toh unhein saaf karein
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
                
            return json.loads(text_response.strip())
            
        except json.JSONDecodeError:
            print("[Error] Model ne invalid JSON return kiya hai.")
            return {}
        except Exception as e:
            print(f"[Ollama JSON Error] {e}")
            return {}

# Singleton pattern taake project mein har jagah ek hi instance use ho
_client = None

def get_client():
    global _client
    if _client is None:
        _client = LocalOllamaClient(model="qwen2.5:7b")
    return _client

