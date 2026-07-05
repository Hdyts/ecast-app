"""
eCast — Translation Module
Machine translation using the unified LLM.
- AR→EN: Direct translation
- AR→ID: Direct translation
"""

import logging
from typing import Optional

from app.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class Translator:
    """
    Handles Arabic → Indonesian and Arabic → English translation
    using the unified LLM.
    """

    def __init__(self):
        self._llm_manager = LLMManager()

    @property
    def available_targets(self) -> list[str]:
        """List of supported target languages."""
        return ["id", "en"]

    def load_model(self, target_lang: str) -> None:
        """Load the unified LLM."""
        self._llm_manager.load_model()

    def unload_model(self, target_lang: str) -> None:
        """Unload models to free memory."""
        self._llm_manager.unload_model()

    def translate_batch(
        self,
        texts: list[str],
        target_lang: str,
        batch_size: Optional[int] = None,
        progress_callback: Optional[callable] = None,
    ) -> list[str]:
        """
        Translate a list of Arabic texts to the target language directly.

        Args:
            texts: List of Arabic text strings to translate.
            target_lang: Target language code ('id' or 'en').
            batch_size: Ignored, texts are processed sequentially by the LLM.
            progress_callback: Optional callback(current, total).

        Returns:
            List of translated text strings.
        """
        if not texts:
            return []

        self.load_model(target_lang)

        if target_lang not in self.available_targets:
            raise ValueError(f"Unsupported target language: {target_lang}")

        language_map = {
            "en": "English",
            "id": "Indonesian"
        }
        
        target_lang_full = language_map[target_lang]

        system_prompt = (
            f"You are a professional translator. "
            f"Translate the following Arabic text directly into {target_lang_full}. "
            f"Output only the translated text, without any explanations or additional comments."
        )

        translations = []
        total = len(texts)

        for i, text in enumerate(texts):
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
                
                # Temperature 0.1 for high fidelity translation
                translated_text = self._llm_manager.generate_chat(
                    messages=messages,
                    max_tokens=1024,
                    temperature=0.1
                )
                
                translations.append(translated_text)
            except Exception as e:
                logger.error(f"Translation error at index {i}: {e}")
                translations.append("[Translation Error]")

            if progress_callback:
                progress_callback(i + 1, total)

        return translations

    def translate_text(self, text: str, target_lang: str) -> str:
        """Translate a single Arabic text string."""
        if not text.strip():
            return ""
        results = self.translate_batch([text], target_lang)
        return results[0] if results else ""

    def is_loaded(self, target_lang: str) -> bool:
        """Check if models for a target language are loaded."""
        return self._llm_manager.is_loaded()

    def get_status(self) -> dict:
        """Return current status of loaded models."""
        return {
            "loaded_models": ["Qwen2.5-3B-Instruct"] if self.is_loaded("id") else [],
            "available_targets": self.available_targets,
        }

