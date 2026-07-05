"""
eCast — Summarization Module
Abstractive Arabic text summarization using LLM.
"""

import logging
from typing import Optional

from app.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class Summarizer:
    """
    Handles abstractive Arabic text summarization using the unified LLM.
    Supports chunking for long texts.
    """

    def __init__(self):
        self._llm_manager = LLMManager()

    def load_model(self) -> None:
        """Load the summarization model lazily."""
        self._llm_manager.load_model()

    def unload_model(self) -> None:
        """Unload model to free memory."""
        self._llm_manager.unload_model()

    def _chunk_text(self, text: str, max_words: int = 300) -> list[str]:
        """Split text semantically by sentences, then group into chunks."""
        from app.preprocessor import ArabicPreprocessor
        
        preprocessor = ArabicPreprocessor()
        # Clean text slightly before segmenting, but keep it mostly intact
        clean_text = preprocessor.clean_text(text, remove_tashkeel=False, normalize=True)
        # Segment into sentences (max 500 characters per segment to ensure safe limits)
        sentences = preprocessor.segment_sentences(clean_text, max_length=500)
        
        chunks = []
        current_chunk = []
        current_words = 0
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            if current_words + sentence_words > max_words and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_words = sentence_words
            else:
                current_chunk.append(sentence)
                current_words += sentence_words
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks

    def summarize(
        self, 
        text: str, 
        progress_callback: Optional[callable] = None,
        progress_offset: int = 0,
        progress_total: int = 1
    ) -> str:
        """
        Summarize a long Arabic text by chunking it.
        
        Args:
            text: Arabic text to summarize.
            progress_callback: Optional callback(current, total) for progress.
            progress_offset: Starting progress value.
            progress_total: Total progress value.
            
        Returns:
            Summarized Arabic text.
        """
        if not text.strip():
            return ""

        self.load_model()
        
        # Split text into chunks semantically to avoid cutting sentences in half
        # Increased chunk size since LLM has 4096 ctx
        chunks = self._chunk_text(text, max_words=600)
        total_chunks = len(chunks)
        summaries = []

        logger.info(f"Summarizing text in {total_chunks} chunks...")

        system_prompt = (
            "You are an expert summarizer. "
            "Summarize the following Arabic text into concise, clear Arabic. "
            "Output only the summary in Arabic, without any extra text or explanations."
        )

        for i, chunk in enumerate(chunks):
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chunk}
                ]
                
                # Temperature 0.3 for more focused and deterministic summaries
                summary_chunk = self._llm_manager.generate_chat(
                    messages=messages,
                    max_tokens=300,
                    temperature=0.3
                )
                    
                summaries.append(summary_chunk)
                
            except Exception as e:
                logger.error(f"Summarization error at chunk {i}: {e}")
                
            if progress_callback and progress_total > 0:
                # Map chunk progress to the overall progress range
                chunk_progress = int((i + 1) / total_chunks * (progress_total - progress_offset))
                done = progress_offset + chunk_progress
                progress_callback(done, progress_total)
                
        final_summary = " ".join(summaries)
        
        # Recursive Summarization: If the final summary is still huge (e.g. > 1000 words), summarize it again.
        if len(final_summary.split()) > 1000:
            logger.info("Summary is very long, applying recursive summarization...")
            return self.summarize(final_summary)
        
        return final_summary

