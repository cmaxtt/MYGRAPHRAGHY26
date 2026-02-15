"""
Document ingestor for processing PDF, DOCX, XLSX, CSV, and TXT files.
Uses Docling for parsing and Ollama for triplet extraction.
"""
import os
import json
import logging
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from tenacity import retry, stop_after_attempt, wait_exponential

from base_ingestor import BaseIngestor
from config import settings


logger = logging.getLogger(__name__)


class Ingestor(BaseIngestor):
    """Document ingestor for processing files with Docling and Ollama."""
    
    def __init__(self, db=None):
        """
        Initialize document ingestor.
        
        Args:
            db: Database instance (optional)
        """
        super().__init__(db)
        self.converter = DocumentConverter()
        self.chunker = HybridChunker()
    
    def process_file(self, file_path: str) -> None:
        """
        Process a single file: parse, chunk, embed, extract triplets.
        
        Args:
            file_path: Path to the file
        """
        logger.info(f"Processing {file_path}...")
        result = self.converter.convert(file_path)
        doc = result.document
        chunks = list(self.chunker.chunk(doc))
        
        logger.info(f"  Ingesting {len(chunks)} chunks in parallel...")
        with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS or min(32, os.cpu_count() + 4)) as executor:
            list(executor.map(lambda x: self._process_chunk(x[1], x[0], file_path), enumerate(chunks)))
    
    def _process_chunk(self, chunk, index: int, file_path: str) -> None:
        """
        Process a single chunk: store vector and extract/store triplets.
        
        Args:
            chunk: Docling chunk object
            index: Chunk index
            file_path: Source file path
        """
        text = chunk.text
        # 1. Store in Vector DB (PostgreSQL)
        embedding = self.get_embedding(text)
        self.store_vector(text, embedding, {"source": file_path, "chunk_id": index})
        
        # 2. Extract Triplets and Store in Graph DB (Neo4j)
        triplets = self.extract_triplets(text)
        self.store_triplets(triplets)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def extract_triplets(self, text: str) -> List[Dict]:
        """
        Extract semantic triplets (subject-predicate-object) from text using LLM.
        
        Args:
            text: Text to extract triplets from
            
        Returns:
            List of triplets as dicts with 'subject', 'predicate', 'object' keys
        """
        import ollama
        
        prompt = f"""
        Extract semantic triplets (Subject, Predicate, Object) from the following text.
        Return ONLY a JSON list of objects with "subject", "predicate", and "object" keys.
        Do not include any explanation.
        
        Text: {text}
        """
        try:
            response = ollama.generate(model=self.llm_model, prompt=prompt, format="json")
            data = json.loads(response['response'])
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "triplets" in data:
                return data["triplets"]
            return []
        except Exception as e:
            logger.error(f"Error extracting triplets: {e}")
            return []


if __name__ == "__main__":
    # Test with a dummy file if needed, but primarily used by app.py
    pass