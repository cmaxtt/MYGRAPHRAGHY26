"""
Base ingestor class with common functionality for document and clinical data ingestion.
"""
import os
import json
import logging
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from db import Database
from config import settings


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
        self.embed_model = settings.EMBED_MODEL
        self.llm_model = settings.LLM_MODEL
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using Ollama."""
        import ollama
        response = ollama.embeddings(model=self.embed_model, prompt=text)
        return response['embedding']
    
    def store_vector(self, text: str, embedding: List[float], metadata: Dict) -> None:
        """
        Store text with embedding in PostgreSQL vector database.
        
        Args:
            text: The text content
            embedding: Vector embedding
            metadata: JSON metadata
        """
        conn = self.db.connect_pg()
        if not conn:
            logger.error("Failed to connect to PostgreSQL")
            return
        try:
            conn.autocommit = True
            with conn.cursor() as cur:
                self._store_vector_with_cursor(cur, text, embedding, metadata)
        except Exception as e:
            logger.error(f"Error storing vector: {e}")
            raise
        finally:
            self.db.release_pg(conn)
    
    def _store_vector_with_cursor(self, cur, text: str, embedding: List[float], metadata: Dict) -> None:
        """
        Store vector using an existing cursor (for batch operations).
        
        Args:
            cur: PostgreSQL cursor
            text: Text content
            embedding: Vector embedding
            metadata: JSON metadata
        """
        cur.execute(
            "INSERT INTO chunks (content, metadata, embedding) VALUES (%s, %s, %s)",
            (text, json.dumps(metadata), embedding)
        )
    
    def store_triplets(self, triplets: List[Dict]) -> None:
        """
        Store triplets (subject-predicate-object) in Neo4j graph database.
        
        Args:
            triplets: List of dicts with 'subject', 'predicate', 'object' keys
        """
        driver = self.db.connect_neo4j()
        with driver.session() as session:
            for t in triplets:
                # Basic cleaning
                s = str(t.get('subject', '')).strip()
                p = str(t.get('predicate', '')).strip().upper().replace(" ", "_")
                o = str(t.get('object', '')).strip()
                
                if s and p and o:
                    query = f"""
                    MERGE (s:Entity {{name: $s_name}})
                    MERGE (o:Entity {{name: $o_name}})
                    MERGE (s)-[r:{p}]->(o)
                    """
                    try:
                        session.run(query, s_name=s, o_name=o)
                    except Exception as e:
                        logger.error(f"Error storing triplet {s}-{p}-{o}: {e}")
    
    def close(self) -> None:
        """Close database connections."""
        self.db.close()