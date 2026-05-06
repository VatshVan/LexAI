"""
LexAI — PyMuPDF OCR Engine (Primary)

Handles:
- Text-based PDFs (direct text extraction, no OCR needed)
- Image-based PDFs (rasterize then extract via Tesseract per-page fallback)
"""
from __future__ import annotations

from pathlib import Path

import structlog

from apps.core.exceptions import OCRExtractionError
from infrastructure.ocr.base import BaseOCREngine, OCRResult

logger = structlog.get_logger(__name__)

# Minimum characters per page to consider direct extraction successful.
# Below this threshold, the page is likely a scanned image.
MIN_TEXT_LENGTH_THRESHOLD = 50


class PyMuPDFEngine(BaseOCREngine):
    """
    Primary OCR engine using PyMuPDF (fitz).

    Strategy:
    1. Attempt direct text extraction per page.
    2. If a page yields < MIN_TEXT_LENGTH_THRESHOLD chars, rasterize to
       image and run pytesseract on that page.
    3. Report engine_used as "pymupdf" or "pymupdf+tesseract" accordingly.
    """

    def extract(self, file_path: Path) -> OCRResult:
        logger.info("pymupdf_extract_start", file_path=str(file_path))

        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise OCRExtractionError(
                message="PyMuPDF is not installed",
                detail=str(e),
            )

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            raise OCRExtractionError(
                message=f"Failed to open document: {file_path.name}",
                detail=str(e),
            )

        page_texts: list[str] = []
        used_tesseract = False

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").strip()

                if len(text) < MIN_TEXT_LENGTH_THRESHOLD:
                    # Page likely scanned — rasterize and OCR
                    text = self._ocr_page_with_tesseract(page, page_num)
                    if text:
                        used_tesseract = True

                page_texts.append(text)

            raw_text = "\n\n".join(page_texts)
            engine_used = "pymupdf+tesseract" if used_tesseract else "pymupdf"

            logger.info(
                "pymupdf_extract_complete",
                file_path=str(file_path),
                page_count=len(doc),
                engine_used=engine_used,
                char_count=len(raw_text),
            )

            return OCRResult(
                raw_text=raw_text,
                page_texts=page_texts,
                page_count=len(doc),
                engine_used=engine_used,
                confidence_score=None,
            )
        except OCRExtractionError:
            raise
        except Exception as e:
            raise OCRExtractionError(
                message=f"PyMuPDF extraction failed for {file_path.name}",
                detail=str(e),
            )
        finally:
            doc.close()

    def _ocr_page_with_tesseract(self, page, page_num: int) -> str:
        """Rasterize a PDF page to image and run Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
            import io

            # Rasterize page at 300 DPI for good OCR quality
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            text = pytesseract.image_to_string(img).strip()

            logger.debug(
                "tesseract_page_ocr",
                page_num=page_num,
                char_count=len(text),
            )
            return text

        except ImportError:
            logger.warning("tesseract_not_available", page_num=page_num)
            return ""
        except Exception as e:
            logger.warning(
                "tesseract_page_ocr_failed",
                page_num=page_num,
                error=str(e),
            )
            return ""
