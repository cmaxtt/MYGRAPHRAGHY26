
import os
import csv
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

# Import existing modules
from base_ingestor import BaseIngestor
try:
    from config import settings
except ImportError:
    # Fallback/Mock for standalone testing if needed
    class Settings:
        BATCH_SIZE_EMBEDDINGS = 10
    settings = Settings()

logger = logging.getLogger(__name__)

class SQLIngestor(BaseIngestor):
    """
    Ingestor for SQL Query/Natural Language pairs from CSV.
    Transforms data into Vector and Graph records using LLM.
    """

    SYSTEM_PROMPT = """
You are a Data Ingestion Engine for a Hybrid RAG System. Your goal is to transform CSV data into structured JSON for dual-storage.

Output Requirements:

Vector Store Object: A flattened text chunk containing the semantic intent of the query and the SQL logic for embedding.

Graph Store Object: Atomic entities (Queries, Tables, Columns) and their relationships (ACCESSES, FILTERS_BY).

Constraints:

Output ONLY valid JSON.
No conversational filler.
Maintain strict data types (Strings for IDs, ISO 8601 for dates).
IDs for Query nodes should be the provided ID from input.

JSON Schema Template:

{
  "vector_record": {
    "id": "string",
    "content": "Query: [QueryText] | SQL: [GeneratedSQL]",
    "metadata": { "source": "training_set", "table_refs": ["list"], "type": "string" }
  },
  "graph_record": {
    "nodes": [
      {"id": "Q1", "label": "Query", "properties": {"text": "..."}},
      {"id": "tblInvoices", "label": "Table", "properties": {"name": "..."}}
    ],
    "edges": [
      {"from": "Q1", "to": "tblInvoices", "type": "ACCESSES"}
    ]
  }
}
"""

    def __init__(self, db=None):
        super().__init__(db)

    async def process_csv(self, file_path: str) -> None:
        """
        Reads CSV, processes each row with LLM, and stores in DBs.
        Assumes CSV has headers like 'id', 'query', 'sql'.
        """
        logger.info(f"Processing CSV: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return

        rows = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        
        logger.info(f"Found {len(rows)} rows to process.")
        
        # Initialize DBs
        await self.db.init_db()

        # Process sequentially (or batched)
        for i, row in enumerate(rows):
            logger.info(f"Processing row {i+1}/{len(rows)}: ID={row.get('id', 'N/A')}")
            try:
                # 1. Transform with LLM
                structured_data = await self._transform_row(row)
                if not structured_data:
                    continue

                # 2. Store in Vector DB (Postgres)
                await self._store_vector_record(structured_data.get("vector_record"))

                # 3. Store in Graph DB (Neo4j)
                await self._store_graph_record(structured_data.get("graph_record"))

            except Exception as e:
                logger.error(f"Error processing row {i}: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _transform_row(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Sends row data to LLM to get structured JSON.
        """
        user_prompt = f"""
        Process this data row:
        ID: {row.get('id', 'unknown')}
        Query: {row.get('query', '')}
        SQL: {row.get('sql', '')}
        """

        try:
            response = await self.api_client.get_completion(
                user_prompt, 
                system_prompt=self.SYSTEM_PROMPT
            )
            
            # Simple cleanup for JSON parsing
            cleaned = response.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"LLM Transformation failed: {e}")
            return None

    async def _store_vector_record(self, record: Dict[str, Any]) -> None:
        """
        Stores the vector record in Postgres.
        """
        if not record:
            return

        content = record.get("content", "")
        metadata = record.get("metadata", {})
        # Flatten metadata for storage if needed, or keep as JSONB
        
        # Generate embedding
        embedding = await self.get_embedding(content)

        # We can reuse the generic `store_vector` or specific logic
        # For this architecture, we might want to use the `query_embeddings` table logic 
        # but the prompt output is generic. Let's map it to `chunks` for now OR 
        # map to `query_embeddings` if it fits better.
        # Given the "Retrieval" plan uses `query_embeddings`, let's try to fit it there 
        # or use `chunks` if it's purely for vector search.
        # The prompt output `vector_record` structure is generic.
        # Let's use the BaseIngestor's store_vector which maps to `chunks` table for simplicity first,
        # OR better, let's map it to `query_embeddings` to keep the SQL-specific metadata.
        
        # Mapping to query_embeddings columns
        sql_query = content.split("| SQL:")[1].strip() if "| SQL:" in content else ""
        question = content.split("| SQL:")[0].replace("Query:", "").strip()
        
        await self.db.insert_query_embedding(
            question=question,
            sql_query=sql_query,
            embedding=embedding,
            description=content, # Store full content string here
            query_type=metadata.get("type"),
            associated_tables=metadata.get("table_refs"),
            table_links=None,
            used_columns=None
        )
        logger.info(f"Stored vector record for: {question[:30]}...")

    async def _store_graph_record(self, record: Dict[str, Any]) -> None:
        """
        Stores nodes and edges in Neo4j.
        """
        if not record:
            return

        nodes = record.get("nodes", [])
        edges = record.get("edges", [])

        driver = await self.db.get_neo4j_driver()
        async with driver.session() as session:
            # 1. Merge Nodes
            for node in nodes:
                label = node.get("label", "Entity")
                props = node.get("properties", {})
                node_id = node.get("id")
                
                # Cypher query generation (simple version)
                # Assuming 'id' in properties is the unique key, or using the input 'id'
                # The prompt asks for "id" at top level.
                
                # Construct SET clause dynamically
                set_clauses = []
                params = {"id": node_id}
                
                for k, v in props.items():
                    key_safe = k.replace(" ", "_")
                    set_clauses.append(f"n.{key_safe} = ${key_safe}")
                    params[key_safe] = v

                query = f"MERGE (n:{label} {{id: $id}}) "
                if set_clauses:
                    query += "SET " + ", ".join(set_clauses)
                
                await session.run(query, **params)

            # 2. Merge Edges
            for edge in edges:
                src = edge.get("from")
                tgt = edge.get("to")
                rel_type = edge.get("type", "RELATED_TO")
                
                query = f"""
                MATCH (a {{id: $src}})
                MATCH (b {{id: $tgt}})
                MERGE (a)-[r:{rel_type}]->(b)
                """
                await session.run(query, src=src, tgt=tgt)

        logger.info(f"Stored {len(nodes)} nodes and {len(edges)} edges in Graph.")

if __name__ == "__main__":
    # Test run
    async def main():
        ingestor = SQLIngestor()
        # Create a dummy CSV if not exists for testing
        test_csv = "data/training_data.csv"
        if not os.path.exists(test_csv):
            os.makedirs("data", exist_ok=True)
            with open(test_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "query", "sql"])
                writer.writerow(["1", "Show me the top 5 customers by sales", "SELECT c.name, SUM(s.amount) FROM customers c JOIN sales s ON c.id = s.customer_id GROUP BY c.name ORDER BY 2 DESC LIMIT 5"])
                writer.writerow(["2", "List all products in the Electronics category", "SELECT * FROM products WHERE category = 'Electronics'"])
        
        await ingestor.process_csv(test_csv)
        await ingestor.close()

    asyncio.run(main())
