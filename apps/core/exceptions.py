"""
LexAI — Domain Exceptions & Global DRF Exception Handler

All service-layer code raises these domain exceptions.
Views/DRF translates them to HTTP responses via lexai_exception_handler.
"""
from rest_framework.views import exception_handler
from rest_framework import status

from apps.core.response import api_response


# ─── Base Exception ────────────────────────────────────
class LexAIException(Exception):
    """Base exception for all LexAI domain errors."""

    def __init__(self, message: str = "", detail: str = ""):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


# ─── Document Domain ──────────────────────────────────
class DocumentProcessingError(LexAIException):
    """Raised when document processing pipeline fails."""
    pass


class UnsupportedFileTypeError(LexAIException):
    """Raised when an uploaded file's MIME type is not allowed."""
    pass


class DuplicateDocumentError(LexAIException):
    """Raised when a file with the same SHA-256 hash already exists."""

    def __init__(self, message: str = "", detail: str = "", existing_document_id: str = ""):
        super().__init__(message, detail)
        self.existing_document_id = existing_document_id


# ─── OCR Domain ───────────────────────────────────────
class OCRExtractionError(LexAIException):
    """Raised when OCR text extraction fails."""
    pass


# ─── Chunking Domain ──────────────────────────────────
class ChunkingError(LexAIException):
    """Raised when document chunking fails."""
    pass


# ─── Embedding Domain ─────────────────────────────────
class EmbeddingServiceError(LexAIException):
    """Raised when embedding generation fails."""
    pass


# ─── Vector Store Domain ──────────────────────────────
class VectorStoreError(LexAIException):
    """Raised when vector store operations fail."""
    pass


# ─── Exception → HTTP Status Mapping ──────────────────
_EXCEPTION_STATUS_MAP = {
    UnsupportedFileTypeError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    DuplicateDocumentError: status.HTTP_409_CONFLICT,
    DocumentProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    OCRExtractionError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ChunkingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    EmbeddingServiceError: status.HTTP_502_BAD_GATEWAY,
    VectorStoreError: status.HTTP_503_SERVICE_UNAVAILABLE,
    LexAIException: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def lexai_exception_handler(exc, context):
    """
    Global DRF exception handler.
    Handles LexAI domain exceptions + standard DRF exceptions.
    All responses use the standard API envelope.
    """
    # Let DRF handle its own exceptions first (auth, throttle, validation, etc.)
    response = exception_handler(exc, context)

    if response is not None:
        # Wrap DRF's response in our envelope
        return api_response(
            success=False,
            error=str(exc.detail) if hasattr(exc, "detail") else str(exc),
            status_code=response.status_code,
        )

    # Handle LexAI domain exceptions
    if isinstance(exc, LexAIException):
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        for exc_class, code in _EXCEPTION_STATUS_MAP.items():
            if isinstance(exc, exc_class):
                http_status = code
                break

        error_data = {"message": exc.message}
        if exc.detail:
            error_data["detail"] = exc.detail
        if isinstance(exc, DuplicateDocumentError) and exc.existing_document_id:
            error_data["existing_document_id"] = exc.existing_document_id

        return api_response(
            success=False,
            error=error_data,
            status_code=http_status,
        )

    # Unhandled exceptions — return generic 500
    return api_response(
        success=False,
        error="Internal server error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
