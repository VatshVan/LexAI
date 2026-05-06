from uuid import UUID
from django.conf import settings
from .base import BaseAgent
from .schemas import RetrievalOutput, RetrievedChunk
from apps.documents.services.embedding import EmbeddingService
from apps.vector_store.repository import VectorRepository
from apps.vector_store.schemas import SearchResult
from apps.documents.services.lineage import LineageMetadata
from apps.claude_client.client import get_claude
import structlog

log = structlog.get_logger()


class RetrievalAgent(BaseAgent):
    agent_name = "Retrieval"

    def _execute(
        self,
        session_id: UUID,
        query_id: UUID,
        rewritten_query: str,
        target_document_types: list[str],
        top_k: int = None,
        min_score: float = None,
    ) -> RetrievalOutput:
        top_k = top_k or settings.DEFAULT_TOP_K
        min_score = min_score or settings.MIN_RELEVANCE_SCORE
        embedding = EmbeddingService().embed_query(rewritten_query)
        repo = VectorRepository()

        # Strategy A: filtered
        results = repo.semantic_search(
            session_id=str(session_id),
            query_embedding=embedding,
            top_k=top_k,
            filter_metadata={"document_type": {"$in": target_document_types}}
            if target_document_types else None,
        )
        strategy = "filtered"

        # Strategy B: broad fallback
        if len(results) < 3:
            results = repo.semantic_search(
                session_id=str(session_id),
                query_embedding=embedding,
                top_k=top_k,
            )
            strategy = "broad"

        # Strategy C: query expansion
        if len(results) < 3:
            expanded = get_claude().haiku("query_rewriting", rewritten_query)
            embedding2 = EmbeddingService().embed_query(expanded.strip())
            results = repo.semantic_search(
                session_id=str(session_id),
                query_embedding=embedding2,
                top_k=top_k,
            )
            strategy = "expanded"

        filtered = [r for r in results if r.relevance_score >= min_score]
        chunks = [self._to_chunk(r) for r in filtered]
        return RetrievalOutput(
            query_id=query_id,
            retrieved_chunks=chunks,
            total_retrieved=len(chunks),
            retrieval_strategy=strategy,
        )

    def _to_chunk(self, r: SearchResult) -> RetrievedChunk:
        m = r.metadata
        return RetrievedChunk(
            vector_id=r.id,
            text=r.text,
            relevance_score=r.relevance_score,
            page_number=m.page_number if isinstance(m, LineageMetadata) else m.get("page_number"),
            section_label=m.section_label if isinstance(m, LineageMetadata) else m.get("section_label", ""),
            document_id=m.document_id if isinstance(m, LineageMetadata) else m.get("document_id", ""),
            document_title=m.document_title if isinstance(m, LineageMetadata) else m.get("document_title", ""),
            document_type=m.document_type if isinstance(m, LineageMetadata) else m.get("document_type", ""),
            chunk_index=m.chunk_index if isinstance(m, LineageMetadata) else m.get("chunk_index", 0),
            text_hash=m.text_hash if isinstance(m, LineageMetadata) else m.get("text_hash", ""),
        )
