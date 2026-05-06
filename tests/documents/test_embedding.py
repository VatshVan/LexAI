"""
LexAI — Embedding Service Tests
"""
import pytest
from unittest.mock import patch, MagicMock

from apps.documents.services.embedding import EmbeddingService, EmbeddingResult


class TestEmbeddingService:
    """Tests for the embedding service with primary/fallback strategy."""

    def test_embed_texts_returns_embedding_result(self):
        """Test that embed_texts returns proper EmbeddingResult."""
        service = EmbeddingService()

        # Mock the local model since we don't want to download models in tests
        mock_model = MagicMock()
        mock_model.encode.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]
        service._local_model = mock_model

        # Force fallback (no Voyage API key)
        with patch.object(service, "_get_voyage_client", return_value=None):
            result = service.embed_texts(["text one", "text two"])

        assert isinstance(result, EmbeddingResult)
        assert len(result.vectors) == 2
        assert result.dimensions == 3

    def test_embed_query_returns_single_vector(self):
        """Test that embed_query returns a single vector."""
        service = EmbeddingService()

        mock_model = MagicMock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
        service._local_model = mock_model

        with patch.object(service, "_get_voyage_client", return_value=None):
            vector = service.embed_query("test query")

        assert isinstance(vector, list)
        assert len(vector) == 3

    def test_fallback_activates_without_api_key(self):
        """Test that local model is used when Voyage API key is missing."""
        service = EmbeddingService()

        mock_model = MagicMock()
        mock_model.encode.return_value = [[0.1, 0.2]]
        service._local_model = mock_model

        with patch("django.conf.settings.VOYAGE_API_KEY", ""):
            result = service.embed_texts(["test"])

        assert result.model_used == "BAAI/bge-large-en-v1.5"
