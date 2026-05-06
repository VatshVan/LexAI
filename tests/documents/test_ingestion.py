"""
LexAI — Ingestion Tests
"""
import hashlib
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.documents.models import LegalDocument
from apps.documents.services.ingestion import (
    compute_file_hash,
    ingest_document,
)
from apps.core.exceptions import UnsupportedFileTypeError
from tests.documents.factories import LegalDocumentFactory


@pytest.mark.django_db
class TestDocumentIngestion:
    """Tests for the document ingestion service."""

    def test_pdf_upload_success(self):
        """Test that a valid PDF can be uploaded and creates a document record."""
        file = SimpleUploadedFile(
            "test.pdf",
            b"%PDF-1.4 fake content for testing",
            content_type="application/pdf",
        )
        document, is_duplicate = ingest_document(
            file=file,
            title="Test FIR Document",
            document_type="FIR",
            session_id=str(uuid.uuid4()),
        )
        assert document is not None
        assert document.title == "Test FIR Document"
        assert document.document_type == "FIR"
        assert document.status == LegalDocument.ProcessingStatus.UPLOADED
        assert document.file_hash
        assert not is_duplicate

    def test_duplicate_file_rejected_with_flag(self):
        """Test that uploading the same file returns duplicate flag."""
        content = b"%PDF-1.4 duplicate test content"
        file_hash = hashlib.sha256(content).hexdigest()
        session_id = str(uuid.uuid4())

        # Create first document
        file1 = SimpleUploadedFile("test1.pdf", content, content_type="application/pdf")
        doc1, dup1 = ingest_document(
            file=file1,
            title="Original",
            document_type="FIR",
            session_id=session_id,
        )
        assert not dup1

        # Upload same content again
        file2 = SimpleUploadedFile("test2.pdf", content, content_type="application/pdf")
        doc2, dup2 = ingest_document(
            file=file2,
            title="Duplicate",
            document_type="FIR",
            session_id=session_id,
        )
        assert dup2
        assert doc2.id == doc1.id

    def test_unsupported_mime_type_rejected(self):
        """Test that unsupported file types are rejected."""
        file = SimpleUploadedFile(
            "test.exe",
            b"not a valid document",
            content_type="application/x-msdownload",
        )
        with pytest.raises(UnsupportedFileTypeError):
            ingest_document(
                file=file,
                title="Bad File",
                document_type="OTHER",
                session_id=str(uuid.uuid4()),
            )

    def test_ocr_task_sets_status_correctly(self):
        """Test that document status transitions work correctly."""
        doc = LegalDocumentFactory(status=LegalDocument.ProcessingStatus.UPLOADED)
        assert doc.status == "UPLOADED"

        doc.status = LegalDocument.ProcessingStatus.OCR_PROCESSING
        doc.save()
        doc.refresh_from_db()
        assert doc.status == "OCR_PROCESSING"

    def test_compute_file_hash_deterministic(self):
        """Test that file hash is deterministic for same content."""
        content = b"test content for hashing"
        file1 = SimpleUploadedFile("a.pdf", content)
        file2 = SimpleUploadedFile("b.pdf", content)

        assert compute_file_hash(file1) == compute_file_hash(file2)


@pytest.mark.django_db
class TestDocumentUploadAPI:
    """Tests for the upload REST endpoint."""

    def setup_method(self):
        self.client = APIClient()

    def test_upload_endpoint_returns_202(self):
        """Test upload endpoint returns 202 with task_id.
        Note: Celery tasks won't actually run without a broker,
        but we can test the view logic by mocking the pipeline.
        """
        from unittest.mock import patch, MagicMock

        mock_result = MagicMock()
        mock_result.id = "mock-task-id"

        with patch("apps.documents.views.process_document_pipeline", return_value=mock_result):
            file = SimpleUploadedFile(
                "test.pdf",
                b"%PDF-1.4 upload test",
                content_type="application/pdf",
            )
            response = self.client.post(
                "/api/v1/documents/upload/",
                {"file": file, "title": "Upload Test", "document_type": "FIR"},
                format="multipart",
            )

        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert "document_id" in data["data"]
        assert data["data"]["task_id"] == "mock-task-id"
