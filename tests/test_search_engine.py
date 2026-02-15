"""
Tests for search engine (search.py).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from search import SearchEngine


class TestSearchEngine:
    """Test SearchEngine class."""

    def test_init(self):
        """Test initialization."""
        mock_db = Mock()
        engine = SearchEngine(db=mock_db)
        assert engine.db is mock_db
        assert engine.embed_model is not None
        assert engine.llm_model is not None

    @patch("search.ollama")
    def test_get_embedding(self, mock_ollama):
        """Test get_embedding method."""
        mock_ollama.embeddings.return_value = {"embedding": [0.1, 0.2]}
        mock_db = Mock()
        engine = SearchEngine(db=mock_db)
        result = engine.get_embedding("query")
        mock_ollama.embeddings.assert_called_once_with(
            model=engine.embed_model, prompt="query"
        )
        assert result == [0.1, 0.2]

    def test_vector_search(self):
        """Test vector_search method."""
        mock_db = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.connect_pg.return_value = mock_conn
        mock_conn.cursor.return_value = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.fetchall.return_value = [("chunk1",), ("chunk2",)]

        engine = SearchEngine(db=mock_db)
        embedding = [0.1, 0.2]
        results = engine.vector_search(embedding, top_k=5)

        mock_db.connect_pg.assert_called_once()
        mock_cursor.execute.assert_called_once()
        assert results == ["chunk1", "chunk2"]

    @patch("search.ollama")
    def test_extract_entities(self, mock_ollama):
        """Test extract_entities method."""
        mock_ollama.generate.return_value = {"response": "Alice, Bob, Company"}

        mock_db = Mock()
        engine = SearchEngine(db=mock_db)
        entities = engine.extract_entities("Who are Alice and Bob?")

        mock_ollama.generate.assert_called_once()
        assert entities == ["Alice", "Bob", "Company"]

    def test_graph_search(self):
        """Test graph_search method."""
        mock_db = Mock()
        mock_driver = Mock()
        mock_session = Mock()
        mock_result = Mock()
        mock_record = MagicMock()

        mock_db.connect_neo4j.return_value = mock_driver
        mock_driver.session.return_value = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_session.run.return_value = [mock_record]

        # Mock record fields
        mock_record.__getitem__.side_effect = lambda key: {
            "s": "Alice",
            "s_pid": None,
            "s_vid": None,
            "s_did": None,
            "p": "KNOWS",
            "o": "Bob",
            "o_pid": None,
            "o_vid": None,
            "o_did": None,
            "s_label": "Person",
            "o_label": "Person",
            "p2": None,
            "g": None,
            "g_mid": None,
            "g_label": None,
        }[key]

        engine = SearchEngine(db=mock_db)
        entities = ["Alice"]
        results = engine.graph_search(entities)

        mock_db.connect_neo4j.assert_called_once()
        mock_session.run.assert_called_once()
        assert len(results) > 0

    @patch("search.ollama")
    def test_generate_answer(self, mock_ollama):
        """Test generate_answer method."""
        mock_ollama.generate.return_value = {"response": "The answer is 42."}

        mock_db = Mock()
        engine = SearchEngine(db=mock_db)
        answer = engine.generate_answer("query", "context")

        mock_ollama.generate.assert_called_once()
        assert answer == "The answer is 42."

    def test_get_all_graph_data(self):
        """Test get_all_graph_data method."""
        mock_db = Mock()
        mock_driver = Mock()
        mock_session = Mock()
        mock_node_result = MagicMock()
        mock_edge_result = MagicMock()

        mock_db.connect_neo4j.return_value = mock_driver
        mock_driver.session.return_value = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_session.run.side_effect = [
            mock_node_result,  # nodes
            mock_edge_result,  # edges
        ]

        # Mock records
        class MockRecord:
            def __init__(self, data):
                self.data = data

            def __getitem__(self, key):
                return self.data[key]

        mock_node_record = MockRecord(
            {"id": "Alice", "label": "Alice", "type": "Entity"}
        )
        mock_node_result.__iter__.return_value = iter([mock_node_record])

        mock_edge_record = MockRecord(
            {"source": "Alice", "label": "KNOWS", "target": "Bob"}
        )
        mock_edge_result.__iter__.return_value = iter([mock_edge_record])

        engine = SearchEngine(db=mock_db)
        nodes, edges = engine.get_all_graph_data()

        assert len(nodes) == 1
        assert len(edges) == 1
        assert nodes[0]["id"] == "Alice"
        assert edges[0]["source"] == "Alice"
