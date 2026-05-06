"""
LexAI — ChromaDB Singleton Client

Thread-safe singleton returning a persistent ChromaDB client.
Collection naming convention: "session_{session_id}"
"""
from __future__ import annotations

import threading

import chromadb
import structlog
from django.conf import settings

logger = structlog.get_logger(__name__)


class ChromaClientSingleton:
    """
    Thread-safe singleton for ChromaDB PersistentClient.

    Ensures only one ChromaDB client instance exists per process.
    CHROMA_PERSIST_DIR is read from Django settings.
    """

    _instance: chromadb.PersistentClient | None = None
    _lock = threading.Lock()

    @classmethod
    def get_client(cls) -> chromadb.PersistentClient:
        """Return the singleton ChromaDB client, creating it if needed."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    persist_dir = getattr(settings, "CHROMA_PERSIST_DIR", "./chroma_data")
                    logger.info("chroma_client_init", persist_dir=persist_dir)
                    cls._instance = chromadb.PersistentClient(path=str(persist_dir))
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing only)."""
        with cls._lock:
            cls._instance = None

    @classmethod
    def collection_name(cls, session_id: str) -> str:
        """Generate collection name from session ID."""
        return f"session_{session_id}"
