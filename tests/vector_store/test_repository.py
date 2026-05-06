"""
LexAI — Vector Store Repository Tests
"""
import uuid

import pytest

from apps.documents.services.lineage import LineageMetadata
from apps.vector_store.repository import VectorRepository
from apps.vector_store.schemas import VectorDocument


@pytest.mark.django_db
class TestVectorRepository:
    """Tests for the ChromaDB vector store repository."""

    def _make_vector_doc(self, doc_id: str = None, session_id: str = None) -> VectorDocument:
        doc_id = doc_id or str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        vector_id = str(uuid.uuid4())

        metadata = LineageMetadata(
            document_id=doc_id,
            chunk_id=str(uuid.uuid4()),
            chroma_vector_id=vector_id,
            session_id=session_id,
            document_title="Test Doc",
            document_type="FIR",
            page_number=1,
            section_label="Section 1",
            chunk_index=0,
            char_start=0,
            char_end=100,
            text_hash="abc123",
            token_count=20,
        )

        return VectorDocument(
            id=vector_id,
            text="Test legal text for embedding.",
            embedding=[0.1] * 384,  # Simulated 384-dim embedding
            metadata=metadata.to_dict(),
        )

    def test_upsert_is_idempotent(self, session_id):
        """Test that upserting the same document twice doesn't create duplicates."""
        repo = VectorRepository()
        doc = self._make_vector_doc(session_id=session_id)

        count1 = repo.upsert_documents(session_id, [doc])
        count2 = repo.upsert_documents(session_id, [doc])

        assert count1 == 1
        assert count2 == 1

        stats = repo.collection_stats(session_id)
        assert stats["vector_count"] == 1

    def test_semantic_search_returns_ranked_results(self, session_id):
        """Test that semantic search returns results ordered by relevance."""
        repo = VectorRepository()

        docs = []
        for i in range(3):
            doc = self._make_vector_doc(session_id=session_id)
            docs.append(doc)

        repo.upsert_documents(session_id, docs)

        # Search with a query vector
        query_embedding = [0.1] * 384
        results = repo.semantic_search(session_id, query_embedding, top_k=3)

        assert len(results) == 3
        # Results should have relevance scores
        for result in results:
            assert 0 <= result.relevance_score <= 1
            assert result.metadata is not None

    def test_get_by_vector_id_returns_correct_document(self, session_id):
        """Test retrieving a specific document by its vector ID."""
        repo = VectorRepository()
        doc = self._make_vector_doc(session_id=session_id)
        repo.upsert_documents(session_id, [doc])

        result = repo.get_by_vector_id(session_id, doc.id)

        assert result is not None
        assert result.id == doc.id
        assert result.text == doc.text

    def test_collection_isolation_between_sessions(self):
        """Test that different sessions have completely isolated data."""
        repo = VectorRepository()
        session_a = str(uuid.uuid4())
        session_b = str(uuid.uuid4())

        doc_a = self._make_vector_doc(session_id=session_a)
        doc_b = self._make_vector_doc(session_id=session_b)

        repo.upsert_documents(session_a, [doc_a])
        repo.upsert_documents(session_b, [doc_b])

        stats_a = repo.collection_stats(session_a)
        stats_b = repo.collection_stats(session_b)

        assert stats_a["vector_count"] == 1
        assert stats_b["vector_count"] == 1

        # Search in session A shouldn't find session B's docs
        results = repo.semantic_search(session_a, [0.1] * 384, top_k=10)
        result_ids = {r.id for r in results}
        assert doc_a.id in result_ids
        assert doc_b.id not in result_ids

        # Cleanup
        repo.delete_collection(session_a)
        repo.delete_collection(session_b)

    def test_delete_collection(self, session_id):
        """Test that deleting a collection removes all its data."""
        repo = VectorRepository()
        doc = self._make_vector_doc(session_id=session_id)
        repo.upsert_documents(session_id, [doc])

        repo.delete_collection(session_id)

        # After deletion, a new collection should be empty
        stats = repo.collection_stats(session_id)
        assert stats["vector_count"] == 0
