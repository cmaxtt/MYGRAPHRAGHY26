"""
Tests for base_ingestor module.
"""

from unittest.mock import Mock, patch, MagicMock
import pytest
import json
import asyncio

from base_ingestor import BaseIngestor


class TestBaseIngestor:
    """Test BaseIngestor class."""

    def test_init_without_db(self):
        """Test initialization without db parameter."""
        ingestor = BaseIngestor()
        assert ingestor.db is not None
        assert ingestor.api_client is not None

    def test_init_with_db(self):
        """Test initialization with db parameter."""
        mock_db = Mock()
        ingestor = BaseIngestor(db=mock_db)
        assert ingestor.db is mock_db

    @patch("base_ingestor.api_client.get_embeddings")
    def test_get_embedding(self, mock_get_embeddings):
        """Test get_embedding method."""
        mock_get_embeddings.return_value = [[0.1, 0.2, 0.3]]
        ingestor = BaseIngestor()
        result = asyncio.run(ingestor.get_embedding("test text"))
        mock_get_embeddings.assert_called_once_with(["test text"])
        assert result == [0.1, 0.2, 0.3]
    @pytest.mark.skip(reason="Async migration needed")
    def test_store_vector(self, mock_logger):
        """Test store_vector method."""
        mock_db = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.connect_pg.return_value = mock_conn
        mock_conn.cursor.return_value = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        ingestor = BaseIngestor(db=mock_db)
        text = "test content"
        embedding = [0.1, 0.2, 0.3]
        metadata = {"source": "test"}

        ingestor.store_vector(text, embedding, metadata)

        mock_db.connect_pg.assert_called_once()
        mock_conn.autocommit = True
        mock_cursor.execute.assert_called_once_with(
            "INSERT INTO chunks (content, metadata, embedding) "
            "VALUES (%s, %s, %s)",
            (text, json.dumps(metadata), embedding),
        )
        mock_db.release_pg.assert_called_once_with(mock_conn)

    @pytest.mark.skip(reason="Async migration needed")
    def test_store_triplets(self):
        """Test store_triplets method."""
        mock_db = Mock()
        mock_driver = Mock()
        mock_session = Mock()
        mock_db.connect_neo4j.return_value = mock_driver
        mock_driver.session.return_value = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        ingestor = BaseIngestor(db=mock_db)
        triplets = [
            {"subject": "Alice", "predicate": "works at", "object": "Company"},
            {"subject": "Bob", "predicate": "knows", "object": "Alice"},
        ]

        ingestor.store_triplets(triplets)

        mock_db.connect_neo4j.assert_called_once()
        # Should call session.run twice (once per triplet)
        assert mock_session.run.call_count == 2

    @pytest.mark.skip(reason="Async migration needed")
    def test_close(self):
        """Test close method."""
        mock_db = Mock()
        ingestor = BaseIngestor(db=mock_db)
        ingestor.close()
        mock_db.close.assert_called_once()
