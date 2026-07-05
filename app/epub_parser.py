"""
eCast — ePub Parser Module
Extracts Arabic text content from .epub files using ebooklib + BeautifulSoup4.
"""

import re
from pathlib import Path
from typing import Optional

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


class EpubParser:
    """Parses .epub files and extracts text content per chapter."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"ePub file not found: {self.file_path}")
        if self.file_path.suffix.lower() != ".epub":
            raise ValueError(f"Invalid file format: {self.file_path.suffix}. Only .epub is supported.")

        self.book: Optional[epub.EpubBook] = None
        self._chapters: list[dict] = []

    def load(self) -> "EpubParser":
        """Load and parse the ePub file."""
        try:
            self.book = epub.read_epub(str(self.file_path), options={"ignore_ncx": True})
        except Exception as e:
            raise RuntimeError(f"Failed to parse ePub file: {e}")
        self._extract_chapters()
        return self

    def _extract_chapters(self) -> None:
        """Extract all document items (chapters) from the ePub."""
        if self.book is None:
            raise RuntimeError("Book not loaded. Call load() first.")

        self._chapters = []
        items = list(self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

        chapter_index = 0
        for item in items:
            content = item.get_content()
            if not content:
                continue

            soup = BeautifulSoup(content, "lxml")
            text = self._extract_text(soup)

            # Skip empty or very short content (navigation pages, etc.)
            if not text or len(text.strip()) < 20:
                continue

            # Try to extract the chapter title
            title = self._extract_title(soup, chapter_index)

            # Count words (Arabic words split by whitespace)
            word_count = len(text.split())

            self._chapters.append({
                "index": chapter_index,
                "title": title,
                "text": text.strip(),
                "word_count": word_count,
                "item_name": item.get_name(),
            })
            chapter_index += 1

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract clean text from HTML, preserving paragraph structure."""
        # Remove script and style elements
        for tag in soup(["script", "style", "meta", "link", "head"]):
            tag.decompose()

        # Extract text from paragraphs and headers
        text_parts = []
        for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "span", "li"]):
            element_text = element.get_text(separator=" ", strip=True)
            if element_text:
                text_parts.append(element_text)

        # If no structured content found, fallback to full text
        if not text_parts:
            full_text = soup.get_text(separator="\n", strip=True)
            text_parts = [line.strip() for line in full_text.split("\n") if line.strip()]

        # Join with newlines to preserve paragraph breaks
        text = "\n".join(text_parts)

        # Clean up excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        return text

    def _extract_title(self, soup: BeautifulSoup, fallback_index: int) -> str:
        """Extract chapter title from HTML content."""
        # Try heading tags in priority order
        for tag in ["h1", "h2", "h3", "title"]:
            heading = soup.find(tag)
            if heading:
                title_text = heading.get_text(strip=True)
                if title_text and len(title_text) < 200:
                    return title_text

        return f"الفصل {fallback_index + 1}"  # "Chapter X" in Arabic

    def get_chapters(self) -> list[dict]:
        """Return list of all chapters with metadata."""
        return [
            {
                "index": ch["index"],
                "title": ch["title"],
                "word_count": ch["word_count"],
                "preview": ch["text"][:200] + "..." if len(ch["text"]) > 200 else ch["text"],
            }
            for ch in self._chapters
        ]

    def get_chapter_text(self, chapter_index: int) -> str:
        """Get full text of a specific chapter."""
        for ch in self._chapters:
            if ch["index"] == chapter_index:
                return ch["text"]
        raise IndexError(f"Chapter index {chapter_index} not found. Available: {[c['index'] for c in self._chapters]}")

    def get_chapters_text(self, chapter_indices: list[int]) -> dict[int, str]:
        """Get full text for multiple chapters."""
        result = {}
        for idx in chapter_indices:
            result[idx] = self.get_chapter_text(idx)
        return result

    def get_book_metadata(self) -> dict:
        """Extract book metadata (title, author, language)."""
        if self.book is None:
            raise RuntimeError("Book not loaded. Call load() first.")

        def _get_meta(field: str) -> str:
            try:
                values = self.book.get_metadata("DC", field)
                if values:
                    return values[0][0] if isinstance(values[0], tuple) else str(values[0])
            except Exception:
                pass
            return "Unknown"

        return {
            "title": _get_meta("title"),
            "author": _get_meta("creator"),
            "language": _get_meta("language"),
            "total_chapters": len(self._chapters),
            "total_words": sum(ch["word_count"] for ch in self._chapters),
        }
