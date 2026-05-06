"""
LexAI — Abstract OCR Engine Interface (Strategy Pattern)

All OCR engines implement BaseOCREngine. The factory function
selects the appropriate engine based on MIME type.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OCRResult:
    """Structured result from OCR text extraction."""

    raw_text: str
    page_texts: list[str] = field(default_factory=list)
    page_count: int = 0
    engine_used: str = ""
    confidence_score: float | None = None

    @property
    def has_text(self) -> bool:
        return bool(self.raw_text.strip())


class BaseOCREngine(ABC):
    """Abstract OCR engine interface. All engines must implement extract()."""

    @abstractmethod
    def extract(self, file_path: Path) -> OCRResult:
        """
        Extract text from a PDF or image file.

        Args:
            file_path: Path to the file to process.

        Returns:
            OCRResult with extracted text, per-page texts, and metadata.

        Raises:
            OCRExtractionError: If text extraction fails.
        """
        ...
