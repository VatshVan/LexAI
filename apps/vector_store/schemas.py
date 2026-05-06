"""
LexAI — Vector Store Typed Schemas

Typed input/output schemas for all vector store operations.
Used as inter-service contracts between the document domain and vector store.
"""
from __future__ import annotations

from dataclasses import dataclass

from apps.documents.services.lineage import LineageMetadata


@dataclass
class VectorDocument:
    """Input schema for upserting a document into the vector store."""

    id: str  # chroma_vector_id from LineageMetadata
    text: str
    embedding: list[float]
    metadata: dict  # Serialized LineageMetadata via to_dict()


@dataclass
class SearchResult:
    """Output schema for a single search result from the vector store."""

    id: str
    text: str
    metadata: LineageMetadata  # Deserialized back to typed object
    distance: float
    relevance_score: float  # 1 - distance, normalized to [0, 1]
