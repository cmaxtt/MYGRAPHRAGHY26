"""
Base ingestor class with common functionality for document and clinical data ingestion.
"""

import os
import json
import logging
import asyncio
import re
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from db import Database
from config import settings
from api_client import api_client

logger = logging.getLogger(__name__)


class BaseIngestor:
    """Base class for all ingestors providing common database operations."""

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize base ingestor.

        Args:
            db: Database instance (optional, creates new if not provided)
        """
        self.db = db or Database()
        self.api_client = api_client

    @staticmethod
    def _sanitize_relationship_type(rel_type: str) -> str:
        """
        Sanitize relationship type for Neo4j.
        Only allows alphanumeric characters and underscores.
        """
        # Remove any non-alphanumeric/underscore characters
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "", rel_type)
        # Ensure it's not empty
        return sanitized if sanitized else "RELATES_TO"

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using DeepSeek/OpenAI API."""
        # Wrap single text in list for the batch API
        embeddings = await self.api_client.get_embeddings([text])
        return embeddings[0]

    async def store_vector(
        self, text: str, embedding: List[float], metadata: Dict
    ) -> None:
        """
        Store text with embedding in PostgreSQL vector database.

        Args:
            text: The text content
            embedding: Vector embedding
            metadata: JSON metadata
        """
        pool = await self.db.get_pg_pool()
        if not pool:
            logger.error("Failed to connect to PostgreSQL")
            return
        try:
            async with pool.acquire() as conn:
                await self._store_vector_with_conn(conn, text, embedding, metadata)
        except Exception as e:
            logger.error(f"Error storing vector: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def store_vectors_batch(
        self, texts: List[str], embeddings: List[List[float]], metadatas: List[Dict]
    ) -> None:
        """
        Store multiple texts with embeddings in PostgreSQL vector database in batch.

        Args:
            texts: List of text contents
            embeddings: List of vector embeddings
            metadatas: List of JSON metadata
        """
        if len(texts) != len(embeddings) or len(texts) != len(metadatas):
            raise ValueError("Lists must have same length")

        pool = await self.db.get_pg_pool()
        if not pool:
            logger.error("Failed to connect to PostgreSQL")
            return

        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    for text, embedding, metadata in zip(texts, embeddings, metadatas):
                        await self._store_vector_with_conn(
                            conn, text, embedding, metadata
                        )
        except Exception as e:
            logger.error(f"Error storing vectors batch: {e}")
            raise

    async def _store_vector_with_conn(
        self, conn, text: str, embedding: List[float], metadata: Dict
    ) -> None:
        """
        Store vector using an existing connection (for batch operations).
        """
        await conn.execute(
            "INSERT INTO chunks (content, metadata, embedding) VALUES ($1, $2, $3)",
            text,
            json.dumps(metadata),
            embedding,
        )

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def store_triplets(self, triplets: List[Dict]) -> None:
        """
        Store triplets (subject-predicate-object) in Neo4j graph database.

        Args:
            triplets: List of dicts with 'subject', 'predicate', 'object' keys
        """
        driver = await self.db.get_neo4j_driver()
        async with driver.session() as session:
            for t in triplets:
                # Basic cleaning
                s = str(t.get("subject", "")).strip()
                p = str(t.get("predicate", "")).strip().upper().replace(" ", "_")
                o = str(t.get("object", "")).strip()

                if s and p and o:
                    # Sanitize relationship type
                    p_sanitized = self._sanitize_relationship_type(p)
                    # Build query safely
                    query = (
                        "MERGE (s:Entity {name: $s_name}) "
                        "MERGE (o:Entity {name: $o_name}) "
                        "MERGE (s)-[r:" + p_sanitized + "]->(o)"
                    )
                    try:
                        await session.run(query, s_name=s, o_name=o)  # type: ignore
                    except Exception as e:
                        logger.error(
                            f"Error storing triplet {s}-{p_sanitized}-{o}: {e}"
                        )

    async def close(self) -> None:
        """Close database connections."""
        await self.db.close()
