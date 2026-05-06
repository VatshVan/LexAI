"""
LexAI — Vector Store Repository

All vector store operations. Parts 2 and 3 interact with ChromaDB
ONLY through this repository — never directly.
"""
from __future__ import annotations

import structlog

from apps.core.exceptions import VectorStoreError
from apps.documents.services.lineage import LineageMetadata
from apps.vector_store.client import ChromaClientSingleton
from apps.vector_store.schemas import SearchResult, VectorDocument

logger = structlog.get_logger(__name__)


class VectorRepository:
    """
    Repository pattern wrapping all ChromaDB operations.
    Swapping to Qdrant or FAISS requires only reimplementing this class.
    """

    def __init__(self):
        self._client = ChromaClientSingleton.get_client()

    def get_or_create_collection(self, session_id: str):
        """
        Get or create a ChromaDB collection for a session.

        Collection name: session_{session_id}
        Ensures complete data isolation between different legal cases.
        """
        name = ChromaClientSingleton.collection_name(session_id)
        try:
            collection = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.debug("collection_accessed", collection=name)
            return collection
        except Exception as e:
            raise VectorStoreError(
                message=f"Failed to access collection for session {session_id}",
                detail=str(e),
            )

    def upsert_documents(
        self,
        session_id: str,
        documents: list[VectorDocument],
    ) -> int:
        """
        Upsert documents into the vector store. Idempotent — safe to re-run.

        Args:
            session_id: The session UUID string.
            documents: List of VectorDocument to upsert.

        Returns:
            Count of upserted vectors.
        """
        if not documents:
            return 0

        log = logger.bind(session_id=session_id, count=len(documents))
        log.info("upsert_start")

        try:
            collection = self.get_or_create_collection(session_id)

            # ChromaDB batch upsert
            ids = [doc.id for doc in documents]
            embeddings = [doc.embedding for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            texts = [doc.text for doc in documents]

            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts,
            )

            log.info("upsert_complete", upserted=len(ids))
            return len(ids)

        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(
                message="Failed to upsert documents into vector store",
                detail=str(e),
            )

    def semantic_search(
        self,
        session_id: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[SearchResult]:
        """
        Semantic search within a session's collection.

        Args:
            session_id: The session UUID string.
            query_embedding: Query vector.
            top_k: Number of results to return.
            filter_metadata: Optional ChromaDB 'where' clause filter.
                Parts 2 & 3 pass filters like {"document_type": "FIR"}.

        Returns:
            Ranked list of SearchResult.
        """
        log = logger.bind(session_id=session_id, top_k=top_k)
        log.info("search_start")

        try:
            collection = self.get_or_create_collection(session_id)

            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if filter_metadata:
                query_params["where"] = filter_metadata

            results = collection.query(**query_params)

            search_results: list[SearchResult] = []

            if results and results["ids"] and results["ids"][0]:
                ids = results["ids"][0]
                documents = results["documents"][0] if results["documents"] else [""] * len(ids)
                metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
                distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)

                for i, vid in enumerate(ids):
                    distance = distances[i] if i < len(distances) else 0.0
                    # Cosine distance → relevance score
                    relevance = max(0.0, min(1.0, 1.0 - distance))

                    metadata_dict = metadatas[i] if i < len(metadatas) else {}
                    try:
                        lineage = LineageMetadata.from_dict(metadata_dict)
                    except (TypeError, KeyError):
                        lineage = None
                        log.warning("metadata_deserialization_failed", vector_id=vid)
                        continue

                    search_results.append(
                        SearchResult(
                            id=vid,
                            text=documents[i] if i < len(documents) else "",
                            metadata=lineage,
                            distance=distance,
                            relevance_score=relevance,
                        )
                    )

            log.info("search_complete", results_count=len(search_results))
            return search_results

        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(
                message="Semantic search failed",
                detail=str(e),
            )

    def get_by_vector_id(
        self,
        session_id: str,
        vector_id: str,
    ) -> VectorDocument | None:
        """
        Retrieve a single document by its vector ID.
        Used by Part 3's fact-checker to retrieve source text by vector ID.
        """
        try:
            collection = self.get_or_create_collection(session_id)
            result = collection.get(
                ids=[vector_id],
                include=["documents", "metadatas", "embeddings"],
            )

            if not result["ids"]:
                return None

            return VectorDocument(
                id=result["ids"][0],
                text=result["documents"][0] if result["documents"] else "",
                embedding=result["embeddings"][0] if result["embeddings"] else [],
                metadata=result["metadatas"][0] if result["metadatas"] else {},
            )
        except Exception as e:
            raise VectorStoreError(
                message=f"Failed to get vector {vector_id}",
                detail=str(e),
            )

    def delete_by_document_id(
        self,
        session_id: str,
        document_id: str,
    ) -> None:
        """Delete all vectors associated with a document from the collection."""
        try:
            collection = self.get_or_create_collection(session_id)
            collection.delete(
                where={"document_id": document_id},
            )
            logger.info("vectors_deleted_for_document", document_id=document_id)
        except Exception as e:
            raise VectorStoreError(
                message=f"Failed to delete vectors for document {document_id}",
                detail=str(e),
            )

    def delete_collection(self, session_id: str) -> None:
        """Delete an entire session's collection. Used for cleanup."""
        name = ChromaClientSingleton.collection_name(session_id)
        try:
            self._client.delete_collection(name=name)
            logger.info("collection_deleted", collection=name)
        except Exception as e:
            logger.warning("collection_delete_failed", collection=name, error=str(e))

    def collection_stats(self, session_id: str) -> dict:
        """
        Return stats for a session's collection.

        Returns:
            {"vector_count": int, "collection_name": str, "session_id": str}
        """
        name = ChromaClientSingleton.collection_name(session_id)
        try:
            collection = self.get_or_create_collection(session_id)
            return {
                "vector_count": collection.count(),
                "collection_name": name,
                "session_id": session_id,
            }
        except Exception as e:
            return {
                "vector_count": 0,
                "collection_name": name,
                "session_id": session_id,
                "error": str(e),
            }
