"""
LexAI — Document Domain Models

LegalDocument: Raw uploaded legal document with full lifecycle tracking.
DocumentChunk: Semantically coherent chunk derived from a LegalDocument.
"""
from django.db import models

from apps.core.models import BaseModel


class LegalDocument(BaseModel):
    """
    Represents a raw uploaded legal document (FIR, affidavit, witness statement).
    Tracks the full lifecycle from upload → OCR → chunked → vectorized.
    """

    class DocumentType(models.TextChoices):
        FIR = "FIR", "First Information Report"
        AFFIDAVIT = "AFFIDAVIT", "Affidavit"
        WITNESS_STATEMENT = "WITNESS_STATEMENT", "Witness Statement"
        BAIL_APPLICATION = "BAIL_APPLICATION", "Bail Application"
        LEGAL_NOTICE = "LEGAL_NOTICE", "Legal Notice"
        OTHER = "OTHER", "Other"

    class ProcessingStatus(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        OCR_PROCESSING = "OCR_PROCESSING", "OCR In Progress"
        OCR_COMPLETE = "OCR_COMPLETE", "OCR Complete"
        CHUNKING = "CHUNKING", "Chunking In Progress"
        EMBEDDING = "EMBEDDING", "Embedding In Progress"
        READY = "READY", "Ready for Querying"
        FAILED = "FAILED", "Processing Failed"

    title = models.CharField(max_length=500)
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    file = models.FileField(upload_to="legal_documents/%Y/%m/%d/")
    file_hash = models.CharField(max_length=64, unique=True, db_index=True)
    file_size_bytes = models.PositiveBigIntegerField()
    mime_type = models.CharField(max_length=100)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.UPLOADED,
    )
    raw_text = models.TextField(blank=True, default="")
    ocr_engine_used = models.CharField(max_length=50, blank=True, default="")
    processing_error = models.TextField(blank=True, default="")
    session_id = models.UUIDField(db_index=True)
    chroma_collection_name = models.CharField(max_length=255, blank=True, default="")

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["session_id", "status"]),
            models.Index(fields=["file_hash"]),
        ]
        verbose_name = "Legal Document"
        verbose_name_plural = "Legal Documents"

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def chunk_count(self) -> int:
        return self.chunks.count()


class DocumentChunk(BaseModel):
    """
    A single semantically coherent chunk derived from a LegalDocument.
    This is the atomic unit stored in ChromaDB. The Django model mirrors
    what's in the vector store to enable SQL-side filtering.
    """

    document = models.ForeignKey(
        LegalDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    chunk_text = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    section_label = models.CharField(max_length=500, blank=True, default="")
    char_start = models.PositiveIntegerField()
    char_end = models.PositiveIntegerField()
    text_hash = models.CharField(max_length=64, db_index=True)
    chroma_vector_id = models.CharField(max_length=255, unique=True)
    token_count = models.PositiveIntegerField()
    is_embedded = models.BooleanField(default=False, db_index=True)

    class Meta(BaseModel.Meta):
        unique_together = [("document", "chunk_index")]
        indexes = [
            models.Index(fields=["document", "is_embedded"]),
        ]
        ordering = ["chunk_index"]
        verbose_name = "Document Chunk"
        verbose_name_plural = "Document Chunks"

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"
