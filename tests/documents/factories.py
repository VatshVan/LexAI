"""
LexAI — Factory Boy Factories for Test Fixtures
"""
import uuid
import hashlib

import factory
from django.core.files.base import ContentFile

from apps.documents.models import LegalDocument, DocumentChunk


class LegalDocumentFactory(factory.django.DjangoModelFactory):
    """Factory for LegalDocument test instances."""

    class Meta:
        model = LegalDocument

    title = factory.Sequence(lambda n: f"Test Document {n}")
    document_type = LegalDocument.DocumentType.FIR
    file = factory.LazyAttribute(
        lambda o: ContentFile(b"fake pdf content", name="test.pdf")
    )
    file_hash = factory.LazyFunction(
        lambda: hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    )
    file_size_bytes = 1024
    mime_type = "application/pdf"
    status = LegalDocument.ProcessingStatus.UPLOADED
    session_id = factory.LazyFunction(uuid.uuid4)


class DocumentChunkFactory(factory.django.DjangoModelFactory):
    """Factory for DocumentChunk test instances."""

    class Meta:
        model = DocumentChunk

    document = factory.SubFactory(LegalDocumentFactory)
    chunk_index = factory.Sequence(lambda n: n)
    chunk_text = factory.Sequence(lambda n: f"This is chunk {n} of the legal document.")
    page_number = 1
    section_label = factory.Sequence(lambda n: f"Section {n}")
    char_start = factory.Sequence(lambda n: n * 100)
    char_end = factory.Sequence(lambda n: (n + 1) * 100)
    text_hash = factory.LazyAttribute(
        lambda o: hashlib.sha256(o.chunk_text.encode()).hexdigest()
    )
    chroma_vector_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    token_count = factory.LazyAttribute(lambda o: len(o.chunk_text.split()))
    is_embedded = False
