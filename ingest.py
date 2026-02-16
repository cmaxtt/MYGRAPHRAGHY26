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
from ingestion.processors import TextProcessor

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
        self.chunker = HybridChunker()  # Use default tokenizer behavior
        self.processor = TextProcessor(api_client)

    async def process_file(
        self, file_path: str, progress_callback: Optional[Callable[[dict], None]] = None
    ) -> None:
        """
        Process a single file: parse, chunk, embed, extract triplets.

        Args:
            file_path: Path to the file
            progress_callback: Optional callback function to report progress
        """
        logger.info(f"Processing {file_path}...")

        # Determine file type
        import os
        file_ext = os.path.splitext(file_path)[1].lower()
        plain_text_extensions = {'.txt', '.sql', '.md', '.csv', '.json', '.xml'}
        
        loop = asyncio.get_running_loop()
        
        if file_ext in plain_text_extensions:
            # Handle plain text files directly
            logger.info(f"Processing plain text file: {file_path}")
            try:
                # Read full text
                full_text = ""
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        full_text = f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        full_text = f.read()
                
                # Extract and store SQL queries from full text
                if full_text and len(full_text.strip()) > 0:
                    try:
                        await self._extract_and_store_sql_queries(full_text, file_path)
                        logger.info(f"SQL query extraction completed for {file_path}")
                    except Exception as e:
                        logger.warning(f"Error extracting SQL queries: {e}")
                
                # Chunk the text using simple paragraph splitting
                chunks = await loop.run_in_executor(None, self.processor.chunk_text_file, file_path)
                
            except Exception as e:
                logger.error(f"Error processing plain text file {file_path}: {e}")
                return
        else:
            # Use docling for complex document formats (PDF, DOCX, XLSX, etc.)
            try:
                result = await loop.run_in_executor(None, self.converter.convert, file_path)
                doc = result.document
                # Extract full text for SQL query detection
                full_text = ""
                try:
                    # Try common attributes for getting full text from docling Document
                    if hasattr(doc, 'text'):
                        full_text = doc.text
                    elif hasattr(doc, 'get_text'):
                        full_text = doc.get_text()
                    else:
                        # Fallback: concatenate chunk texts after chunking
                        pass
                except Exception as e:
                    logger.warning(f"Could not extract full text from document: {e}")
                
                # Extract and store SQL queries from full text if available
                if full_text and len(full_text.strip()) > 0:
                    try:
                        await self._extract_and_store_sql_queries(full_text, file_path)
                        logger.info(f"SQL query extraction completed for {file_path}")
                    except Exception as e:
                        logger.warning(f"Error extracting SQL queries: {e}")
                
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
                progress_callback(
                    {
                        "file": file_path,
                        "total_chunks": total_chunks,
                        "total_batches": total_batches,
                        "current_batch": batch_idx + 1,
                        "chunks_processed": batch_start,
                        "batch_size": len(batch_chunks),
                    }
                )

            await self._process_batch(
                batch_chunks, batch_start, file_path, progress_callback
            )

    async def _process_batch(
        self,
        chunks,
        start_index: int,
        file_path: str,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> None:
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
        logger.debug(
            f"Processing batch of {len(texts)} chunks starting at index {start_index}"
        )

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
            logger.info(
                f"Batch processed {len(texts)} chunks in {duration:.2f}s ({len(texts)/duration:.1f} chunks/s)"
            )

            # Report batch completion
            if progress_callback:
                progress_callback(
                    {
                        "file": file_path,
                        "batch_completed": True,
                        "batch_index": start_index,
                        "batch_size": len(texts),
                        "duration": duration,
                        "chunks_per_second": (
                            len(texts) / duration if duration > 0 else 0
                        ),
                    }
                )

        except Exception as e:
            logger.error(f"Error processing batch starting at index {start_index}: {e}")
            # Report error via callback if available
            if progress_callback:
                progress_callback(
                    {"file": file_path, "error": str(e), "batch_index": start_index}
                )
            raise

    async def _extract_and_store_triplets(self, text: str) -> None:
        """
        Extract triplets from text and store in graph database.
        """
        try:
            triplets = await self.processor.extract_triplets(text)
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
        try:
            embedding = await self.get_embedding(text)
            await self.store_vector(
                text, embedding, {"source": file_path, "chunk_id": index}
            )

            # 2. Extract Triplets and Store in Graph DB (Neo4j)
            triplets = await self.processor.extract_triplets(text)
            if triplets:
                await self.store_triplets(triplets)
        except Exception as e:
            logger.error(f"Error processing chunk {index} of {file_path}: {e}")

    async def _extract_and_store_sql_queries(self, text: str, source: str) -> None:
        """
        Extract SQL queries from text and store in query_embeddings table.
        """
        try:
            sql_queries = await self.processor.extract_sql_queries(text)
            if not sql_queries:
                return
            
            for sql_data in sql_queries:
                sql_query = sql_data.get("sql_query", "").strip()
                if not sql_query:
                    continue
                
                # Generate embedding for the SQL query
                embeddings = await self.api_client.get_embeddings([sql_query])
                embedding = embeddings[0]
                
                # Prepare metadata
                query_type = sql_data.get("query_type")
                tables = sql_data.get("tables", [])
                columns = sql_data.get("columns", [])
                joins = sql_data.get("joins", [])
                
                # Convert joins to table_links format
                table_links = None
                if joins and isinstance(joins, list):
                    table_links = {"joins": joins}
                
                # Store in query_embeddings table
                await self.db.insert_query_embedding(
                    question=sql_query,  # Use SQL as question for now
                    sql_query=sql_query,
                    embedding=embedding,
                    description=f"SQL query extracted from {source}",
                    query_type=query_type,
                    associated_tables=tables,
                    table_links=table_links,
                    used_columns=columns,
                    database_schema="public"
                )
                logger.info(f"Stored SQL query: {query_type} involving {len(tables)} tables")
                
        except Exception as e:
            logger.warning(f"Error storing SQL queries: {e}")


if __name__ == "__main__":
    pass
