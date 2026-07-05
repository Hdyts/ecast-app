"""
eCast — TTS Engine Module
Text-to-Speech synthesis using Edge-TTS with podcast-style audio processing.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

import edge_tts
from pydub import AudioSegment

from app.config import (
    EDGE_TTS_VOICES,
    TTS_SPEED,
    TTS_SAMPLE_RATE,
    PODCAST_SILENCE_MS,
    OUTPUT_FORMAT,
    OUTPUT_DIR,
    FFMPEG_PATH,
    FFPROBE_PATH,
)

import os

# Configure pydub to use the correct ffmpeg and ffprobe binaries
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffmpeg = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH

# Force ffmpeg directory into system PATH for pydub's subprocess calls
_ffmpeg_dir = str(Path(FFMPEG_PATH).parent)
if _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

logger = logging.getLogger(__name__)


class TTSEngine:
    """
    Text-to-Speech engine using Edge-TTS.
    Generates podcast-style audio with natural pacing and silence gaps.
    """

    def __init__(self):
        self._voices = EDGE_TTS_VOICES.copy()

    @property
    def supported_languages(self) -> list[str]:
        """List of supported language codes."""
        return list(self._voices.keys())

    def _get_voice(self, lang: str) -> str:
        """Get Edge-TTS voice name for a language."""
        if lang not in self._voices:
            raise ValueError(f"Unsupported language: {lang}. Supported: {self.supported_languages}")
        return self._voices[lang]

    def _calculate_rate(self) -> str:
        """Convert TTS_SPEED float to Edge-TTS rate string."""
        # Edge-TTS uses percentage format: "+0%", "-10%", "+20%"
        # TTS_SPEED=0.9 means 10% slower → "-10%"
        # TTS_SPEED=1.0 means normal → "+0%"
        # TTS_SPEED=1.1 means 10% faster → "+10%"
        percentage = int((TTS_SPEED - 1.0) * 100)
        if percentage >= 0:
            return f"+{percentage}%"
        return f"{percentage}%"

    async def _synthesize_segment_async(self, text: str, lang: str, output_path: Path) -> Path:
        """
        Synthesize a single text segment to audio file using Edge-TTS.

        Args:
            text: Text to synthesize.
            lang: Language code ('ar', 'id', 'en').
            output_path: Path to save the audio file.

        Returns:
            Path to the generated audio file.
        """
        voice = self._get_voice(lang)
        rate = self._calculate_rate()

        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await communicate.save(str(output_path))

        return output_path

    def synthesize_segment(self, text: str, lang: str, output_path: str | Path) -> Path:
        """
        Synchronous wrapper for synthesizing a single segment.

        Args:
            text: Text to synthesize.
            lang: Language code.
            output_path: Output file path.

        Returns:
            Path to generated audio.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._synthesize_segment_async(text, lang, output_path)
                    )
                    return future.result()
            else:
                return asyncio.run(self._synthesize_segment_async(text, lang, output_path))
        except RuntimeError:
            return asyncio.run(self._synthesize_segment_async(text, lang, output_path))

    async def synthesize_podcast_async(
        self,
        sentences: list[str],
        lang: str,
        output_path: str | Path,
        progress_callback: Optional[callable] = None,
    ) -> Path:
        """
        Generate podcast-style audio from a list of sentences.
        Adds silence gaps between sentences for natural pacing.

        Args:
            sentences: List of text sentences.
            lang: Language code ('ar', 'id', 'en').
            output_path: Final output file path.
            progress_callback: Optional callback(current, total) for progress.

        Returns:
            Path to the final audio file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not sentences:
            raise ValueError("No sentences provided for TTS synthesis.")

        voice = self._get_voice(lang)
        rate = self._calculate_rate()
        total = len(sentences)

        # Generate audio for each sentence
        segment_files: list[Path] = []
        temp_dir = Path(tempfile.mkdtemp(prefix="ecast_tts_"))

        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue

            segment_path = temp_dir / f"segment_{i:04d}.mp3"

            try:
                communicate = edge_tts.Communicate(text=sentence, voice=voice, rate=rate)
                await communicate.save(str(segment_path))
                segment_files.append(segment_path)
            except Exception as e:
                logger.warning(f"TTS failed for sentence {i}: {e}")
                continue

            if progress_callback:
                progress_callback(i + 1, total)

        if not segment_files:
            raise RuntimeError("No audio segments were generated successfully.")

        # Combine segments with silence gaps (podcast style)
        combined = self._combine_segments_with_silence(segment_files)

        # Export to final format
        if OUTPUT_FORMAT == "mp3":
            combined.export(str(output_path), format="mp3", bitrate="192k")
        else:
            combined.export(str(output_path), format=OUTPUT_FORMAT)

        # Cleanup temp files
        for f in segment_files:
            try:
                f.unlink()
            except Exception:
                pass
        try:
            temp_dir.rmdir()
        except Exception:
            pass

        logger.info(f"✓ Podcast audio generated: {output_path} ({lang})")
        return output_path

    def _combine_segments_with_silence(self, segment_files: list[Path]) -> AudioSegment:
        """
        Combine audio segments with silence gaps for podcast feel.

        Args:
            segment_files: List of audio file paths to combine.

        Returns:
            Combined AudioSegment.
        """
        silence = AudioSegment.silent(duration=PODCAST_SILENCE_MS)

        # Start with a short intro silence
        combined = AudioSegment.silent(duration=300)

        for i, seg_path in enumerate(segment_files):
            try:
                segment = AudioSegment.from_file(str(seg_path))
                combined += segment

                # Add silence between sentences (not after the last one)
                if i < len(segment_files) - 1:
                    combined += silence
            except Exception as e:
                logger.warning(f"Failed to load segment {seg_path}: {e}")
                continue

        # Add outro silence
        combined += AudioSegment.silent(duration=500)

        # Normalize volume
        combined = self._normalize_volume(combined)

        return combined

    def _normalize_volume(self, audio: AudioSegment, target_dbfs: float = -20.0) -> AudioSegment:
        """
        Normalize audio volume to a target dBFS level.

        Args:
            audio: Audio segment to normalize.
            target_dbfs: Target volume in dBFS.

        Returns:
            Volume-normalized AudioSegment.
        """
        if audio.dBFS == float("-inf"):
            return audio

        change_in_dbfs = target_dbfs - audio.dBFS
        return audio.apply_gain(change_in_dbfs)

    def synthesize_podcast(
        self,
        sentences: list[str],
        lang: str,
        output_path: str | Path,
        progress_callback: Optional[callable] = None,
    ) -> Path:
        """
        Synchronous wrapper for podcast synthesis.

        Args:
            sentences: List of sentences to synthesize.
            lang: Language code.
            output_path: Output file path.
            progress_callback: Optional progress callback.

        Returns:
            Path to generated audio.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.synthesize_podcast_async(sentences, lang, output_path, progress_callback)
                    )
                    return future.result()
            else:
                return asyncio.run(
                    self.synthesize_podcast_async(sentences, lang, output_path, progress_callback)
                )
        except RuntimeError:
            return asyncio.run(
                self.synthesize_podcast_async(sentences, lang, output_path, progress_callback)
            )

    def get_status(self) -> dict:
        """Return TTS engine status."""
        return {
            "engine": "edge-tts",
            "supported_languages": self.supported_languages,
            "voices": self._voices,
            "speed": TTS_SPEED,
            "silence_ms": PODCAST_SILENCE_MS,
            "output_format": OUTPUT_FORMAT,
        }
