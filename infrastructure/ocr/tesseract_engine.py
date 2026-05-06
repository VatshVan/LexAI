"""
LexAI — Tesseract OCR Engine (Fallback)

Used for pure image files (JPEG, PNG, TIFF).
"""
from __future__ import annotations

from pathlib import Path

import structlog

from apps.core.exceptions import OCRExtractionError
from infrastructure.ocr.base import BaseOCREngine, OCRResult

logger = structlog.get_logger(__name__)


class TesseractEngine(BaseOCREngine):
    """
    Fallback OCR engine using pytesseract for image files.
    Handles JPEG, PNG, TIFF images directly.
    """

    def extract(self, file_path: Path) -> OCRResult:
        logger.info("tesseract_extract_start", file_path=str(file_path))

        try:
            import pytesseract
            from PIL import Image
        except ImportError as e:
            raise OCRExtractionError(
                message="pytesseract or Pillow is not installed",
                detail=str(e),
            )

        try:
            img = Image.open(str(file_path))
            text = pytesseract.image_to_string(img).strip()

            # Attempt to get confidence data
            confidence_score = None
            try:
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                confidences = [
                    int(c) for c in data.get("conf", [])
                    if str(c).isdigit() and int(c) > 0
                ]
                if confidences:
                    confidence_score = sum(confidences) / len(confidences) / 100.0
            except Exception:
                pass

            logger.info(
                "tesseract_extract_complete",
                file_path=str(file_path),
                char_count=len(text),
                confidence=confidence_score,
            )

            return OCRResult(
                raw_text=text,
                page_texts=[text],  # Single page for images
                page_count=1,
                engine_used="tesseract",
                confidence_score=confidence_score,
            )

        except OCRExtractionError:
            raise
        except Exception as e:
            raise OCRExtractionError(
                message=f"Tesseract extraction failed for {file_path.name}",
                detail=str(e),
            )
