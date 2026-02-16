import logging
import json
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class TextProcessor:
    """
    Helper class for processing text content, including chunking and LLM-based extraction.
    """
    
    def __init__(self, api_client):
        self.api_client = api_client

    @staticmethod
    def chunk_text_file(file_path: str) -> List[object]:
        """Read plain text file and chunk it using simple sentence splitting."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 if utf-8 fails
            with open(file_path, 'r', encoding='latin-1') as f:
                text = f.read()
        
        # Simple chunking by paragraphs (double newlines)
        paragraphs = text.split('\n\n')
        chunks = []
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if para:
                # Create a simple chunk object with .text attribute to match docling interface
                chunk = type('Chunk', (), {'text': para})()
                chunks.append(chunk)
        return chunks

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def extract_sql_queries(self, text: str) -> List[Dict]:
        """
        Extract SQL queries and their metadata from text using LLM.
        
        Returns list of dicts with keys: sql_query, query_type, tables, columns, joins
        """
        prompt = f"""
        Extract all SQL queries from the following text. For each query, provide:
        - The exact SQL query text
        - Query type (SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, etc.)
        - List of tables involved
        - List of columns referenced (if any)
        - Join relationships if present (list of joins with from_table, to_table, join_condition)

        Return the result as a JSON list of objects with keys: "sql_query", "query_type", "tables", "columns", "joins".
        If no SQL queries found, return empty list.

        Text: {text}
        """
        try:
            response = await self.api_client.get_completion(prompt)
            cleaned = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "queries" in data:
                return data["queries"]
            return []
        except Exception as e:
            logger.warning(f"Error extracting SQL queries: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def extract_triplets(self, text: str) -> List[Dict]:
        """
        Extract semantic triplets (subject-predicate-object) from text using LLM.
        """
        prompt = f"""
        Extract semantic triplets (Subject, Predicate, Object) from the following text.
        Return ONLY a JSON list of objects with "subject", "predicate", and "object" keys.
        Do not include any explanation or markdown formatting (like ```json).
        
        Text: {text}
        """
        try:
            # Use api_client directly
            response = await self.api_client.get_completion(prompt)

            # Clean response
            cleaned = response.replace("```json", "").replace("```", "").strip()

            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "triplets" in data:
                return data["triplets"]
            return []
        except Exception as e:
            logger.warning(
                f"Error extracting triplets: {e}"
            )  # Warning to avoid spamming errors on bad LLM output
            return []
