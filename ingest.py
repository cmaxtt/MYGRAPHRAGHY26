"""
Document ingestor for processing PDF, DOCX, XLSX, CSV, and TXT files.
Uses Docling for parsing and DeepSeek for triplet extraction.
"""
import os
import json
import logging
import asyncio
import time
from typing import List, Dict, Optional, Callable

# docling might be sync, will run in thread if needed
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from tenacity import retry, stop_after_attempt, wait_exponential

from base_ingestor import BaseIngestor
from config import settings
from api_client import api_client

logger = logging.getLogger(__name__)


class Ingestor(BaseIngestor):
    """Document ingestor for processing files with Docling and DeepSeek."""
    
    def __init__(self, db=None):
        """
        Initialize document ingestor.
        
        Args:
            db: Database instance (optional)
        """
        super().__init__(db)
        # Initialize docling components (sync)
        self.converter = DocumentConverter()
        self.chunker = HybridChunker() # Use default tokenizer behavior

    async def process_file(self, file_path: str, progress_callback: Optional[Callable[[dict], None]] = None) -> None:
        """
        Process a single file: parse, chunk, embed, extract triplets.
        
        Args:
            file_path: Path to the file
            progress_callback: Optional callback function to report progress
        """
        logger.info(f"Processing {file_path}...")
        
        # Run sync docling conversion in thread
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, self.converter.convert, file_path)
            doc = result.document
            # chunking might be fast enough to run in thread or loop, let's run in thread to be safe
            chunks = await loop.run_in_executor(None, list, self.chunker.chunk(doc))
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return

        total_chunks = len(chunks)
        batch_size = settings.BATCH_SIZE_EMBEDDINGS
        total_batches = (total_chunks + batch_size - 1) // batch_size  # ceil division
        
        logger.info(f"  Ingesting {total_chunks} chunks in {total_batches} batches...")
        
        # Process chunks in batches for embedding optimization
        for batch_idx, batch_start in enumerate(range(0, total_chunks, batch_size)):
            batch_end = min(batch_start + batch_size, total_chunks)
            batch_chunks = chunks[batch_start:batch_end]
            
            # Report progress before processing batch
            if progress_callback:
                progress_callback({
                    "file": file_path,
                    "total_chunks": total_chunks,
                    "total_batches": total_batches,
                    "current_batch": batch_idx + 1,
                    "chunks_processed": batch_start,
                    "batch_size": len(batch_chunks)
                })
            
            await self._process_batch(batch_chunks, batch_start, file_path, progress_callback)

    async def _process_batch(self, chunks, start_index: int, file_path: str, progress_callback: Optional[Callable[[dict], None]] = None) -> None:
        """
        Process a batch of chunks: batch embeddings, store vectors, extract triplets.
        
        Args:
            chunks: List of document chunks
            start_index: Starting index of this batch
            file_path: Source file path
            progress_callback: Optional callback function to report progress
        """
        texts = []
        indices = []
        for i, chunk in enumerate(chunks):
            text = chunk.text.strip()
            if text:
                texts.append(text)
                indices.append(start_index + i)
        
        if not texts:
            return
        
        batch_start_time = time.time()
        logger.debug(f"Processing batch of {len(texts)} chunks starting at index {start_index}")
        
        try:
            # Batch embeddings
            embeddings = await self.api_client.get_embeddings(texts)
            
            # Prepare metadata for each chunk
            metadatas = [{"source": file_path, "chunk_id": idx} for idx in indices]
            
            # Batch store vectors
            await self.store_vectors_batch(texts, embeddings, metadatas)
            
            # Extract triplets for each chunk (can be parallel)
            triplet_tasks = []
            for i, chunk in enumerate(chunks):
                text = chunk.text.strip()
                if text:
                    triplet_tasks.append(self._extract_and_store_triplets(text))
            
            if triplet_tasks:
                await asyncio.gather(*triplet_tasks, return_exceptions=True)
            
            duration = time.time() - batch_start_time
            logger.info(f"Batch processed {len(texts)} chunks in {duration:.2f}s ({len(texts)/duration:.1f} chunks/s)")
            
            # Report batch completion
            if progress_callback:
                progress_callback({
                    "file": file_path,
                    "batch_completed": True,
                    "batch_index": start_index,
                    "batch_size": len(texts),
                    "duration": duration,
                    "chunks_per_second": len(texts) / duration if duration > 0 else 0
                })
                
        except Exception as e:
            logger.error(f"Error processing batch starting at index {start_index}: {e}")
            # Report error via callback if available
            if progress_callback:
                progress_callback({
                    "file": file_path,
                    "error": str(e),
                    "batch_index": start_index
                })
            raise
    
    async def _extract_and_store_triplets(self, text: str) -> None:
        """
        Extract triplets from text and store in graph database.
        """
        try:
            triplets = await self.extract_triplets(text)
            if triplets:
                await self.store_triplets(triplets)
        except Exception as e:
            logger.warning(f"Error extracting triplets for text: {e}")

    async def _process_chunk(self, chunk, index: int, file_path: str) -> None:
        """
        Process a single chunk: store vector and extract/store triplets.
        """
        text = chunk.text
        if not text.strip():
            return
            
        # 1. Store in Vector DB (PostgreSQL)
        # Note: Ideally we batch embeddings here too, but for simplicity of migration 
        # and concurrency with semantic extraction, we do per-chunk or relying on base_ingestor 
        # (which currently does single item batch). 
        # If we really want batching here, we should collect all texts first.
        # But let's stick to parallel processing for now as per instructions "Async Support".
        
        try:
            embedding = await self.get_embedding(text)
            await self.store_vector(text, embedding, {"source": file_path, "chunk_id": index})
            
            # 2. Extract Triplets and Store in Graph DB (Neo4j)
            triplets = await self.extract_triplets(text)
            if triplets:
                await self.store_triplets(triplets)
        except Exception as e:
            logger.error(f"Error processing chunk {index} of {file_path}: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
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
            logger.warning(f"Error extracting triplets: {e}") # Warning to avoid spamming errors on bad LLM output
            return []

if __name__ == "__main__":
    pass