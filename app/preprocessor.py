"""
eCast — Arabic Text Preprocessor Module
Cleans, normalizes, and segments Arabic text for translation and TTS.
"""

import re
import json
from pathlib import Path
from typing import Optional


class ArabicPreprocessor:
    """Preprocesses Arabic text: normalization, cleaning, and sentence segmentation."""

    # Arabic diacritics (tashkeel) Unicode range
    TASHKEEL_PATTERN = re.compile(r"[\u0617-\u061A\u064B-\u0652\u0670]")

    # Arabic character normalization map
    NORMALIZATION_MAP = {
        "أ": "ا",  # Alef with Hamza above → Alef
        "إ": "ا",  # Alef with Hamza below → Alef
        "آ": "ا",  # Alef with Madda → Alef
        "ٱ": "ا",  # Alef Wasla → Alef
        "ة": "ه",  # Taa Marbuta → Haa
        "ى": "ي",  # Alef Maqsura → Yaa
        "ؤ": "و",  # Waw with Hamza → Waw
        "ئ": "ي",  # Yaa with Hamza → Yaa
    }

    # Arabic sentence-ending patterns
    SENTENCE_SPLITTER = re.compile(r"(?<=[.!?،؟۔\n])\s+")

    def __init__(self, glossary_path: Optional[str | Path] = None):
        """
        Initialize preprocessor.

        Args:
            glossary_path: Path to Islamic terms glossary JSON file.
        """
        self.glossary: dict = {}
        if glossary_path:
            self._load_glossary(glossary_path)

    def _load_glossary(self, path: str | Path) -> None:
        """Load Islamic terminology glossary from JSON."""
        path = Path(path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.glossary = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARNING] Failed to load glossary: {e}")

    def clean_text(self, text: str, remove_tashkeel: bool = False, normalize: bool = True) -> str:
        """
        Clean and normalize Arabic text.

        Args:
            text: Raw Arabic text.
            remove_tashkeel: Whether to remove diacritical marks.
            normalize: Whether to normalize Arabic characters.

        Returns:
            Cleaned text string.
        """
        if not text:
            return ""

        # Remove HTML tags if any remain
        text = re.sub(r"<[^>]+>", "", text)

        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)

        # Remove email addresses
        text = re.sub(r"\S+@\S+\.\S+", "", text)

        # Remove non-Arabic, non-punctuation special characters (keep Arabic, Latin, numbers, basic punct)
        text = re.sub(r"[^\w\s\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF.!?،؟:;()\"'\-\n]", "", text)

        # Optionally remove diacritics (tashkeel)
        if remove_tashkeel:
            text = self.TASHKEEL_PATTERN.sub("", text)

        # Optionally normalize Arabic characters
        if normalize:
            for original, replacement in self.NORMALIZATION_MAP.items():
                text = text.replace(original, replacement)

        # Normalize whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove leading/trailing whitespace per line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(line for line in lines if line)

        return text.strip()

    def segment_sentences(self, text: str, max_length: int = 500) -> list[str]:
        """
        Split Arabic text into sentences for batch translation.

        Args:
            text: Clean Arabic text.
            max_length: Maximum characters per sentence chunk.

        Returns:
            List of sentence strings.
        """
        if not text:
            return []

        # Split by sentence-ending punctuation
        raw_sentences = self.SENTENCE_SPLITTER.split(text)

        sentences = []
        for sent in raw_sentences:
            sent = sent.strip()
            if not sent:
                continue

            # If sentence is too long, split by newlines then by length
            if len(sent) > max_length:
                sub_parts = sent.split("\n")
                for part in sub_parts:
                    part = part.strip()
                    if not part:
                        continue
                    if len(part) > max_length:
                        # Force split at max_length boundary on word breaks
                        words = part.split()
                        current_chunk = ""
                        for word in words:
                            if len(current_chunk) + len(word) + 1 > max_length:
                                if current_chunk:
                                    sentences.append(current_chunk.strip())
                                current_chunk = word
                            else:
                                current_chunk += " " + word if current_chunk else word
                        if current_chunk:
                            sentences.append(current_chunk.strip())
                    else:
                        sentences.append(part)
            else:
                sentences.append(sent)

        return sentences

    def apply_glossary(self, text: str, target_lang: str) -> str:
        """
        Apply glossary replacements for Islamic terminology.

        Args:
            text: Source Arabic text.
            target_lang: Target language key ('id' or 'en').

        Returns:
            Text with glossary terms annotated/preserved.
        """
        if not self.glossary:
            return text

        for arabic_term, translations in self.glossary.items():
            if arabic_term in text and target_lang in translations:
                # We don't replace in Arabic text; glossary is used post-translation
                pass

        return text

    def get_glossary_translations(self, text: str, target_lang: str) -> dict[str, str]:
        """
        Find glossary terms present in text and return their translations.

        Args:
            text: Arabic text to search in.
            target_lang: Target language key ('id' or 'en').

        Returns:
            Dictionary mapping Arabic terms to their target translations.
        """
        found = {}
        for arabic_term, translations in self.glossary.items():
            if arabic_term in text and target_lang in translations:
                found[arabic_term] = translations[target_lang]
        return found

    def preprocess_for_tts(self, text: str) -> str:
        """
        Prepare text specifically for TTS synthesis.
        Adds natural pauses, normalizes numbers, etc.

        Args:
            text: Clean text for TTS.

        Returns:
            TTS-optimized text.
        """
        # Replace newlines with pause markers
        text = text.replace("\n\n", ". ")
        text = text.replace("\n", ". ")

        # Remove parenthetical references
        text = re.sub(r"\([^)]*\)", "", text)

        # Remove bracket references
        text = re.sub(r"\[[^\]]*\]", "", text)

        # Normalize multiple periods
        text = re.sub(r"\.{2,}", ".", text)

        # Ensure spacing after punctuation
        text = re.sub(r"([.!?،؟])(\S)", r"\1 \2", text)

        # Clean up extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        return text
