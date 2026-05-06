"""
LexAI — Pytest Configuration & Fixtures
"""
import os
import uuid
import tempfile
from pathlib import Path

import pytest
from django.conf import settings


@pytest.fixture(autouse=True)
def use_temp_media(tmp_path, settings):
    """Use a temporary directory for media files during tests."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)


@pytest.fixture(autouse=True)
def use_temp_chroma(tmp_path, settings):
    """Use a temporary directory for ChromaDB during tests."""
    settings.CHROMA_PERSIST_DIR = str(tmp_path / "chroma")
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    # Reset singleton so it picks up new path
    from apps.vector_store.client import ChromaClientSingleton
    ChromaClientSingleton.reset()


@pytest.fixture
def session_id():
    """Generate a random session ID for test isolation."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal valid PDF file for testing."""
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<"
        b"/Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Length 44>>stream\n"
        b"BT /F1 12 Tf 100 700 Td (WHEREAS the party) Tj ET\n"
        b"endstream\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000340 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n434\n%%EOF"
    )
    pdf_path = tmp_path / "test_document.pdf"
    pdf_path.write_bytes(pdf_content)
    return pdf_path
