"""
LexAI — Document Ingestion Service

Handles file upload validation, deduplication, and initial document creation.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import BinaryIO

import structlog
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.core.exceptions import (
    DuplicateDocumentError,
    UnsupportedFileTypeError,
    DocumentProcessingError,
)
from apps.documents.models import LegalDocument

logger = structlog.get_logger(__name__)


def compute_file_hash(file: BinaryIO) -> str:
    """Compute SHA-256 hash of a file. Resets file pointer after reading."""
    sha256 = hashlib.sha256()
    file.seek(0)
    for chunk in iter(lambda: file.read(8192), b""):
        sha256.update(chunk)
    file.seek(0)
    return sha256.hexdigest()


def detect_mime_type(file: UploadedFile) -> str:
    """
    Detect MIME type using python-magic.
    Falls back to the content_type from the upload if magic is unavailable.
    """
    try:
        import magic

        file.seek(0)
        mime = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)
        return mime
    except ImportError:
        logger.warning("python_magic_not_available_using_content_type")
        return file.content_type or "application/octet-stream"
    except Exception as e:
        logger.warning("mime_detection_failed", error=str(e))
        return file.content_type or "application/octet-stream"


def validate_file(file: UploadedFile, mime_type: str) -> None:
    """
    Validate file against allowed types and size limits.

    Raises:
        UnsupportedFileTypeError: If MIME type is not allowed.
        DocumentProcessingError: If file exceeds size limit.
    """
    allowed = settings.ALLOWED_UPLOAD_MIME_TYPES
    if mime_type not in allowed:
        raise UnsupportedFileTypeError(
            message=f"File type '{mime_type}' is not supported",
            detail=f"Allowed types: {', '.join(allowed)}",
        )

    max_size = settings.MAX_UPLOAD_SIZE_BYTES
    if file.size > max_size:
        raise DocumentProcessingError(
            message=f"File size ({file.size} bytes) exceeds limit ({max_size} bytes)",
            detail=f"Maximum upload size is {settings.MAX_UPLOAD_SIZE_MB}MB",
        )


def check_duplicate(file_hash: str) -> LegalDocument | None:
    """
    Check if a document with the same hash already exists.

    Returns:
        The existing LegalDocument if found, None otherwise.
    """
    try:
        return LegalDocument.objects.get(file_hash=file_hash)
    except LegalDocument.DoesNotExist:
        return None


def ingest_document(
    file: UploadedFile,
    title: str,
    document_type: str,
    session_id: str | None = None,
) -> tuple[LegalDocument, bool]:
    """
    Ingest an uploaded document.

    1. Detect MIME type
    2. Validate file type and size
    3. Compute SHA-256 hash
    4. Check for duplicates
    5. Create LegalDocument record

    Args:
        file: The uploaded file
        title: Document title
        document_type: Type of legal document
        session_id: Optional session UUID (generated if not provided)

    Returns:
        Tuple of (LegalDocument, is_duplicate)

    Raises:
        UnsupportedFileTypeError: If file type not allowed
        DocumentProcessingError: If file too large or processing fails
    """
    log = logger.bind(title=title, document_type=document_type)
    log.info("ingestion_start")

    # Generate session_id if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    # Detect and validate MIME type
    mime_type = detect_mime_type(file)
    validate_file(file, mime_type)

    # Compute file hash for deduplication
    file_hash = compute_file_hash(file)
    log = log.bind(file_hash=file_hash, mime_type=mime_type)

    # Check for duplicates
    existing = check_duplicate(file_hash)
    if existing:
        log.info("duplicate_document_detected", existing_id=str(existing.id))
        return existing, True

    # Create document record
    try:
        document = LegalDocument.objects.create(
            title=title,
            document_type=document_type,
            file=file,
            file_hash=file_hash,
            file_size_bytes=file.size,
            mime_type=mime_type,
            session_id=session_id,
            status=LegalDocument.ProcessingStatus.UPLOADED,
        )

        log.info(
            "ingestion_complete",
            document_id=str(document.id),
            session_id=session_id,
        )
        return document, False

    except Exception as e:
        log.error("ingestion_failed", error=str(e))
        raise DocumentProcessingError(
            message="Failed to create document record",
            detail=str(e),
        )
