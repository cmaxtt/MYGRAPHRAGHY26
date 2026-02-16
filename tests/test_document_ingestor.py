"""
Tests for document ingestor (ingest.py).
"""

from unittest.mock import Mock, patch, MagicMock
import pytest
import tempfile
import os

from ingest import Ingestor


class TestDocumentIngestor:
    """Test Ingestor class."""

    def test_init(self):
        """Test initialization."""
        mock_db = Mock()
        ingestor = Ingestor(db=mock_db)
        assert ingestor.db is mock_db
        assert ingestor.converter is not None
        assert ingestor.chunker is not None

    @patch("ingest.DocumentConverter")
    @patch("ingest.HybridChunker")
    @pytest.mark.skip(reason="Migration to DeepSeek")
    def test_process_file(self, mock_chunker, mock_converter):
        """Test process_file method (simplified)."""
        # Mock docling objects
        mock_result = Mock()
        mock_doc = Mock()
        mock_chunk = Mock()
        mock_chunk.text = "chunk text"

        mock_converter.return_value.convert.return_value = mock_result
        mock_result.document = mock_doc
        mock_chunker.return_value.chunk.return_value = [mock_chunk]

        # Mock base class methods
        mock_db = Mock()
        # Mock Neo4j driver for store_triplets (called with empty list)
        mock_driver = Mock()
        mock_session = Mock()
        mock_db.connect_neo4j.return_value = mock_driver
        mock_driver.session.return_value = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        ingestor = Ingestor(db=mock_db)
        ingestor.get_embedding = Mock(return_value=[0.1, 0.2])
        ingestor.store_vector = Mock()
        ingestor.extract_triplets = Mock(return_value=[])

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"dummy content")
            temp_path = f.name

        try:
            ingestor.process_file(temp_path)
            # Verify converter was called
            mock_converter.return_value.convert.assert_called_once_with(
                temp_path
            )
            # Verify chunker was called
            mock_chunker.return_value.chunk.assert_called_once_with(mock_doc)
            # Verify embedding and storage were called
            ingestor.get_embedding.assert_called_once_with("chunk text")
            ingestor.store_vector.assert_called_once()
            ingestor.extract_triplets.assert_called_once_with("chunk text")
        finally:
            os.unlink(temp_path)

    @patch("ollama.generate")
    @pytest.mark.skip(reason="Migration to DeepSeek")
    def test_extract_triplets(self, mock_generate):
        """Test extract_triplets method."""
        mock_db = Mock()
        ingestor = Ingestor(db=mock_db)

        # Mock Ollama response
        mock_generate.return_value = {
            "response": '[{"subject": "Alice", "predicate": "works at", '
            '"object": "Company"}]'
        }

        triplets = ingestor.extract_triplets("some text")

        mock_generate.assert_called_once()
        assert len(triplets) == 1
        assert triplets[0]["subject"] == "Alice"

    @patch("ollama.generate")
    @pytest.mark.skip(reason="Migration to DeepSeek")
    def test_extract_triplets_error(self, mock_generate):
        """Test extract_triplets with error."""
        mock_db = Mock()
        ingestor = Ingestor(db=mock_db)

        mock_generate.side_effect = Exception("API error")

        triplets = ingestor.extract_triplets("some text")
        assert triplets == []
