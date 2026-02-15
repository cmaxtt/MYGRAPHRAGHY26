"""
Pytest configuration and fixtures.
"""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_db():
    """Mock Database instance."""
    db = Mock()
    db.connect_pg = Mock()
    db.release_pg = Mock()
    db.connect_neo4j = Mock()
    db.close = Mock()
    return db


@pytest.fixture
def mock_ollama():
    """Mock Ollama module."""
    with pytest.MonkeyPatch.context():
        import sys

        mock = Mock()
        sys.modules["ollama"] = mock
        yield mock
        del sys.modules["ollama"]
