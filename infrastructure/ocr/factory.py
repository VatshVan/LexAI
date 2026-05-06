"""
LexAI — OCR Engine Factory

Returns the appropriate OCR engine based on file MIME type.
"""
from __future__ import annotations

from infrastructure.ocr.base import BaseOCREngine
from infrastructure.ocr.pymupdf_engine import PyMuPDFEngine
from infrastructure.ocr.tesseract_engine import TesseractEngine
from apps.core.exceptions import UnsupportedFileTypeError


# MIME type → engine mapping
_ENGINE_MAP: dict[str, type[BaseOCREngine]] = {
    "application/pdf": PyMuPDFEngine,
    "image/jpeg": TesseractEngine,
    "image/png": TesseractEngine,
    "image/tiff": TesseractEngine,
}


def get_ocr_engine(mime_type: str) -> BaseOCREngine:
    """
    Returns the appropriate OCR engine based on file MIME type.

    Args:
        mime_type: The MIME type of the file.

    Returns:
        An instance of the appropriate OCR engine.

    Raises:
        UnsupportedFileTypeError: If the MIME type is not supported.
    """
    engine_class = _ENGINE_MAP.get(mime_type)
    if engine_class is None:
        raise UnsupportedFileTypeError(
            message=f"Unsupported file type: {mime_type}",
            detail=f"Supported types: {', '.join(_ENGINE_MAP.keys())}",
        )
    return engine_class()
