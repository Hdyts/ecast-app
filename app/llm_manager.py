import logging
import requests
import json
from threading import Lock

from app.config import (
    OLLAMA_MODEL,
    OLLAMA_CHAT_URL,
)

logger = logging.getLogger(__name__)

class LLMManager:
    """
    Singleton Manager for Ollama REST API requests.
    Using Singleton pattern just to be consistent with previous structure.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LLMManager, cls).__new__(cls)
                cls._instance._is_loaded = True
        return cls._instance

    def load_model(self):
        """Not needed for Ollama as it is an external service."""
        pass

    def unload_model(self):
        """Not needed for Ollama."""
        pass

    def generate_chat(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.3, **kwargs) -> str:
        """
        Generates text using Ollama's chat completion API.
        messages should be a list of dicts like:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama Connection Error: {e}. Is Ollama running?")
            raise RuntimeError(f"Gagal terhubung ke Ollama: {e}")

    def is_loaded(self) -> bool:
        return True
