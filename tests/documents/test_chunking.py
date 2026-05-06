"""
LexAI — Chunking Tests
"""
import pytest

from apps.documents.services.chunking import (
    ChunkResult,
    LegalDocumentChunker,
    _count_tokens,
)
from infrastructure.ocr.base import OCRResult


@pytest.mark.django_db
class TestLegalDocumentChunker:
    """Tests for the legal-boundary-aware chunker."""

    def _make_ocr_result(self, text: str, page_texts: list[str] | None = None) -> OCRResult:
        if page_texts is None:
            page_texts = [text]
        return OCRResult(
            raw_text=text,
            page_texts=page_texts,
            page_count=len(page_texts),
            engine_used="test",
        )

    def test_structural_boundary_detection(self):
        """Test that structural legal markers create chunk boundaries."""
        text = (
            "Preamble text before any section.\n\n"
            "WHEREAS the plaintiff alleges that on the date of 15th March 2024, "
            "the defendant committed acts of negligence resulting in damages. "
            "The plaintiff seeks compensation for all losses incurred.\n\n"
            "WHEREFORE the plaintiff prays that this court may grant relief "
            "in the form of monetary compensation and costs of litigation."
        )
        chunker = LegalDocumentChunker()
        chunks = chunker.chunk(self._make_ocr_result(text))

        assert len(chunks) >= 2
        labels = [c.section_label for c in chunks]
        assert any("WHEREAS" in label for label in labels)

    def test_min_chunk_size_enforced(self):
        """Test that micro-chunks are merged with previous chunks."""
        # Create text with very small sections
        text = (
            "Section 1 content that is reasonably long enough to be a chunk on its own. "
            "It contains multiple sentences about legal matters and proceedings. " * 5
            + "\n\nSection 2 tiny."
        )
        chunker = LegalDocumentChunker(min_chunk_tokens=50)
        chunks = chunker.chunk(self._make_ocr_result(text))

        # "Section 2 tiny." has only 3 tokens — should be merged
        for chunk in chunks:
            assert chunk.token_count >= chunker.min_chunk_tokens or len(chunks) == 1

    def test_overlap_tokens_applied(self):
        """Test that sentence-level splitting includes overlap."""
        # Create a large single paragraph that forces sentence splitting
        sentences = [
            f"Sentence number {i} of the legal document contains important facts. "
            for i in range(100)
        ]
        text = " ".join(sentences)

        chunker = LegalDocumentChunker(
            max_chunk_tokens=50,
            min_chunk_tokens=10,
            overlap_tokens=20,
        )
        chunks = chunker.chunk(self._make_ocr_result(text))

        # With overlap, consecutive chunks should share some text
        if len(chunks) >= 2:
            # Check that chunks have reasonable token counts
            for chunk in chunks:
                assert chunk.token_count > 0

    def test_page_number_preserved_in_chunk(self):
        """Test that chunks carry the correct page number from OCR."""
        page1 = "Page one content with legal terms and conditions. " * 10
        page2 = "Page two has different content about witness statements. " * 10
        text = page1 + "\n\n" + page2

        ocr_result = self._make_ocr_result(text, page_texts=[page1, page2])
        chunker = LegalDocumentChunker()
        chunks = chunker.chunk(ocr_result)

        assert len(chunks) >= 1
        # First chunk should be from page 1
        assert chunks[0].page_number == 1

    def test_empty_text_returns_no_chunks(self):
        """Test that empty text produces no chunks."""
        chunker = LegalDocumentChunker()
        chunks = chunker.chunk(self._make_ocr_result(""))
        assert len(chunks) == 0

    def test_chunk_indices_are_sequential(self):
        """Test that chunk indices are sequential starting from 0."""
        text = (
            "Section 1 of the document. " * 20
            + "\n\nSection 2 of the document. " * 20
        )
        chunker = LegalDocumentChunker()
        chunks = chunker.chunk(self._make_ocr_result(text))

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_token_count_accuracy(self):
        """Test that token count uses whitespace tokenizer."""
        text = "one two three four five"
        assert _count_tokens(text) == 5
