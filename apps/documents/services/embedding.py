import voyageai
from sentence_transformers import SentenceTransformer
from dataclasses import dataclass
from django.conf import settings
import structlog

log = structlog.get_logger()

@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    model_used: str
    dimensions: int  # 1024 for both voyage-law-2 and bge-large


class EmbeddingService:
    """
    Primary:  Voyage AI voyage-law-2 (legal fine-tuned, free 50M tokens)
    Fallback: BAAI/bge-large-en-v1.5 via sentence-transformers (if no key)

    Singleton pattern — model/client loaded once, reused across requests.
    Voyage AI distinguishes query vs document via input_type parameter.
    BGE requires manual prefix for queries.
    """
    _voyage: voyageai.Client | None = None
    _local: SentenceTransformer | None = None

    def _voyage_client(self):
        if not self._voyage and getattr(settings, "VOYAGE_API_KEY", None):
            self._voyage = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        return self._voyage

    def _local_model(self):
        if not self._local:
            log.info("local_embedding_model_loading", model="bge-large-en-v1.5")
            self._local = SentenceTransformer("BAAI/bge-large-en-v1.5")
        return self._local

    def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        """For document chunks at indexing time."""
        client = self._voyage_client()
        if client:
            result = client.embed(texts, model="voyage-law-2",
                                  input_type="document",
                                  truncation=True)
            return EmbeddingResult(result.embeddings, "voyage-law-2", 1024)
        vecs = self._local_model().encode(
            texts, batch_size=32, normalize_embeddings=True).tolist()
        return EmbeddingResult(vecs, "bge-large-en-v1.5", 1024)

    def embed_query(self, query: str) -> list[float]:
        """For semantic search queries at retrieval time."""
        client = self._voyage_client()
        if client:
            result = client.embed([query], model="voyage-law-2",
                                  input_type="query")
            return result.embeddings[0]
        prefix = "Represent this sentence for searching relevant passages: "
        return self._local_model().encode(
            prefix + query, normalize_embeddings=True).tolist()
