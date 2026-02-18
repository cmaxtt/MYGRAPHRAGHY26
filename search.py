import logging
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import List, Dict, Optional
import json
from cachetools import LRUCache

from db import Database
from config import settings
from api_client import api_client

logger = logging.getLogger(__name__)


class SearchEngine:
    def __init__(self, db=None):
        self.db = db or Database()
        self.api_client = api_client
        self.entity_cache = LRUCache(maxsize=1000)

    async def hybrid_search(
        self, query: str, top_k: int = settings.VECTOR_TOP_K
    ) -> Dict:
        """
        Perform hybrid search using async vector and graph lookups.
        """
        # 1. Get Embedding (Async)
        query_embedding_task = self.get_embedding(query)

        # 2. Extract Entities (Async)
        entities_task = self.extract_entities(query)

        # Wait for both initial tasks
        query_embedding, entities = await asyncio.gather(
            query_embedding_task, entities_task
        )

        # 3. Parallel Search Execution
        vector_task = self.vector_search(query_embedding, top_k)
        graph_task = self.graph_search(entities)

        vector_results, graph_results = await asyncio.gather(vector_task, graph_task)

        # 4. Combine Context
        context = "### Vector Context:\n"
        for res in vector_results:
            context += f"- {res}\n"

        context += "\n### Graph Context:\n"
        for res in graph_results:
            context += f"- {res}\n"

        # 5. Generate Answer
        answer = await self.generate_answer(query, context)

        return {
            "answer": answer,
            "sources": {
                "vector_count": len(vector_results),
                "graph_count": len(graph_results),
                "entities_found": entities,
            },
        }

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding via DeepSeek API."""
        embeddings = await self.api_client.get_embeddings([text])
        return embeddings[0]

    async def vector_search(self, embedding: List[float], top_k: int) -> List[str]:
        """Async vector search in PostgreSQL."""
        pool = await self.db.get_pg_pool()
        if not pool:
            return []
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT content FROM chunks 
                    ORDER BY embedding <=> $1::vector 
                    LIMIT $2
                """,
                    embedding,
                    top_k,
                )
                return [row["content"] for row in rows]
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def extract_entities(self, query: str) -> List[str]:
        """Extract entities using DeepSeek Reasoner with caching."""
        # Check cache first
        cached = self.entity_cache.get(query)
        if cached:
            logger.debug(f"Entity cache hit for query: {query}")
            return cached

        prompt = f"""
        Extract the most important specific entities from the following query.
        Look for:
        - Names of people, organizations, or places
        - Specific identifiers or codes
        - Products or items mentioned
        - Key concepts or topics
        
        Return ONLY a comma-separated list of names or IDs. No extra text.
        Query: {query}
        """
        # Using reasoning model for better entity extraction (disamibiguation)
        response = await self.api_client.get_reasoning(prompt)

        # Clean up response (sometimes models add "Here are the entities: ...")
        # Assuming the model follows instructions well, but we can be robust
        clean_response = response.strip()
        if ":" in clean_response:
            # Heuristic: if it looks like "Entities: A, B", take part after colon
            parts = clean_response.split(":")
            if len(parts) > 1:
                clean_response = parts[-1]

        entities = [e.strip() for e in clean_response.split(",") if len(e.strip()) > 1]
        result = entities[:8]

        # Cache the result
        self.entity_cache[query] = result
        logger.debug(f"Cached entities for query: {query}")
        return result

    async def graph_search(self, entities: List[str]) -> List[str]:
        """Async graph search in Neo4j."""
        driver = await self.db.get_neo4j_driver()
        results = []
        async with driver.session() as session:
            for entity in entities:
                query = """
                WITH $name AS searchTerm
                CALL {
                  // Full-text search on name
                  CALL db.index.fulltext.queryNodes("entity_names_index", searchTerm) 
                  YIELD node, score 
                  WHERE score > 0.8
                  RETURN node AS matchedNode
                  LIMIT 5
                  UNION
                  // Exact ID matches
                  MATCH (matchedNode:Entity)
                  WHERE matchedNode.id = searchTerm 
                  RETURN matchedNode
                  LIMIT 5
                }
                WITH DISTINCT matchedNode
                MATCH (matchedNode)-[r]-(neighbor:Entity)
                
                RETURN DISTINCT 
                    matchedNode.name as s, 
                    type(r) as p, 
                    neighbor.name as o, 
                    labels(matchedNode) as s_labels, labels(neighbor) as o_labels
                LIMIT 50
                """
                try:
                    res = await session.run(query, name=entity)
                    async for record in res:

                        def get_label(labels):
                            return next((l for l in labels if l != "Entity"), "Entity")

                        s_label = get_label(record["s_labels"])
                        o_label = get_label(record["o_labels"])

                        s_name = record["s"] or "Unknown"
                        o_name = record["o"] or "Unknown"

                        results.append(
                            f"({s_name}:{s_label}) -[{record['p']}]-> ({o_name}:{o_label})"
                        )


                except Exception as e:
                    logger.error(f"Error in graph search for entity '{entity}': {e}")

        logger.info(
            f"DEBUG: Found {len(results)} graph relationships for entities {entities}"
        )
        return list(set(results))

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_answer(self, query: str, context: str) -> str:
        """Generate final answer using DeepSeek Chat with prompt caching."""
        system_prompt = """
        You are a helpful research assistant. 
        Use the provided context to answer the user query accurately.
        If the context is insufficient, state that clearly.
        """

        prompt = f"""
        Context:
        {context}
        
        User Query: {query}
        """

        return await self.api_client.get_completion(prompt, system_prompt=system_prompt)

    async def get_all_graph_data(self):
        """Async fetch of graph data for visualization."""
        driver = await self.db.get_neo4j_driver()
        nodes = []
        edges = []
        async with driver.session() as session:
            # Get nodes
            node_query = "MATCH (n:Entity) RETURN n.name as id, n.name as label, labels(n)[0] as type LIMIT 100"
            node_res = await session.run(node_query)
            async for record in node_res:
                nodes.append(
                    {
                        "id": record["id"],
                        "label": record["label"],
                        "type": record["type"],
                    }
                )

            # Get edges
            edge_query = "MATCH (s:Entity)-[r]->(o:Entity) RETURN s.name as source, type(r) as label, o.name as target LIMIT 100"
            edge_res = await session.run(edge_query)
            async for record in edge_res:
                edges.append(
                    {
                        "source": record["source"],
                        "label": record["label"],
                        "target": record["target"],
                    }
                )
        return nodes, edges

    async def close(self):
        await self.db.close()


class QuerySearchEngine:
    """Search engine for retrieving SQL queries using semantic similarity and metadata filtering."""
    
    def __init__(self, db=None):
        self.db = db or Database()
        self.api_client = api_client
    
    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def search_sql_queries(
        self, 
        query: str, 
        limit: int = 5,
        query_type: Optional[str] = None,
        tables: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for relevant SQL queries using semantic similarity and optional filters.
        
        Args:
            query: Natural language query about SQL/database schema
            limit: Maximum number of results to return
            query_type: Optional filter by SQL query type (SELECT, INSERT, etc.)
            tables: Optional filter by tables involved
            
        Returns:
            List of dictionaries with query details and similarity scores
        """
        # Get embedding for the natural language query
        embeddings = await self.api_client.get_embeddings([query])
        embedding = embeddings[0]
        
        # Search query_embeddings table
        results = await self.db.search_query_embeddings(
            embedding=embedding,
            limit=limit,
            query_type=query_type,
            tables=tables
        )
        
        # Convert asyncpg records to dicts
        formatted_results = []
        for row in results:
            formatted_results.append({
                "id": row["id"],
                "question": row["question"],
                "sql_query": row["sql_query"],
                "similarity": float(row["similarity"]),
                "tables": row["associated_tables"] or [],
                "table_links": row["table_links"] or {}
            })
        
        return formatted_results
    
    async def get_sql_query_details(self, query_id: int) -> Dict:
        """Get complete details of a specific SQL query by ID."""
        query = await self.db.get_query_by_id(query_id)
        if not query:
            return {}
        
        return {
            "id": query["id"],
            "question": query["question"],
            "description": query["description"],
            "sql_query": query["sql_query"],
            "query_type": query["query_type"],
            "tables": query["associated_tables"] or [],
            "table_links": query["table_links"] or {},
            "used_columns": query["used_columns"] or [],
            "database_schema": query["database_schema"],
            "version": query["version"],
            "is_active": query["is_active"],
            "superseded_by": query["superseded_by"],
            "created_at": query["created_at"].isoformat() if query["created_at"] else None,
            "updated_at": query["updated_at"].isoformat() if query["updated_at"] else None
        }
    
    async def get_all_query_types(self) -> List[str]:
        """Get distinct query types present in the database."""
        pool = await self.db.get_pg_pool()
        if not pool:
            return []
        
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT query_type 
                FROM query_embeddings 
                WHERE query_type IS NOT NULL AND is_active = true
                ORDER BY query_type
            """)
            return [row["query_type"] for row in rows if row["query_type"]]
    
    async def get_all_tables(self) -> List[str]:
        """Get distinct tables referenced in SQL queries."""
        pool = await self.db.get_pg_pool()
        if not pool:
            return []
        
        async with pool.acquire() as conn:
            # Extract unique tables from the array column
            rows = await conn.fetch("""
                SELECT DISTINCT unnest(associated_tables) as table_name
                FROM query_embeddings 
                WHERE associated_tables IS NOT NULL AND is_active = true
                ORDER BY table_name
            """)
            return [row["table_name"] for row in rows if row["table_name"]]
    
    async def get_query_statistics(self) -> Dict:
        """Get statistics about stored SQL queries."""
        pool = await self.db.get_pg_pool()
        if not pool:
            return {}
        
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM query_embeddings WHERE is_active = true")
            by_type_rows = await conn.fetch("""
                SELECT query_type, COUNT(*) as count
                FROM query_embeddings 
                WHERE is_active = true AND query_type IS NOT NULL
                GROUP BY query_type
                ORDER BY count DESC
            """)
            
            by_type = {row["query_type"]: row["count"] for row in by_type_rows}
            
            # Get most recent queries
            recent = await conn.fetch("""
                SELECT id, question, sql_query, created_at
                FROM query_embeddings 
                WHERE is_active = true
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            recent_queries = [
                {
                    "id": row["id"],
                    "question": row["question"][:100] + "..." if len(row["question"]) > 100 else row["question"],
                    "sql_query": row["sql_query"][:100] + "..." if len(row["sql_query"]) > 100 else row["sql_query"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                }
                for row in recent
            ]
            
            return {
                "total_queries": total,
                "queries_by_type": by_type,
                "recent_queries": recent_queries
            }
    
    async def generate_sql_from_natural_language(self, query: str, context_queries: Optional[List[Dict]] = None) -> Dict:
        """
        Use LLM to generate SQL from natural language, augmented with similar stored queries.
        
        Args:
            query: Natural language query about data/schema
            context_queries: Optional pre-fetched similar queries for context
            
        Returns:
            Dictionary with generated SQL and metadata
        """
        if context_queries is None:
            # First, find similar stored queries
            context_queries = await self.search_sql_queries(query, limit=3)
        
        # 2. Graph Traversal: Find related tables/rules for the found queries
        # Gather all tables from the context queries
        tables_to_explore = set()
        for q in context_queries:
            if q.get('tables'):
                tables_to_explore.update(q['tables'])
        
        # Query Neo4j for these tables to find related columns or business rules
        graph_context = []
        if tables_to_explore:
            driver = await self.db.get_neo4j_driver()
            async with driver.session() as session:
                # Find other tables accessed by queries that also access these tables
                # OR find specific metadata about these tables (conceptually)
                # For now, let's find other queries that access the same tables to broaden context
                # OR simply relationships like (Table)-[:HAS_COLUMN]->(Column) if we had that.
                # The prompt said: "Look up the tables identified... in Neo4j to see if there are other related columns or business rules"
                # Since our ingestion creates (Query)-[ACCESSES]->(Table), we can find other queries that access these tables.
                
                table_list = list(tables_to_explore)
                query = """
                MATCH (t:Table) WHERE t.id IN $tables
                MATCH (q:Query)-[:ACCESSES]->(t)
                RETURN t.id as table, collect(q.text)[..3] as related_queries
                """
                try:
                    res = await session.run(query, tables=table_list)
                    async for record in res:
                        graph_context.append(f"Table '{record['table']}' is also used in queries: {record['related_queries']}")
                except Exception as e:
                    logger.warning(f"Graph traversal failed: {e}")

        # Prepare context from similar queries
        context_parts = []
        for i, q in enumerate(context_queries):
            context_parts.append(f"Similar query {i+1} (similarity: {q['similarity']:.3f}):")
            context_parts.append(f"Question: {q['question']}")
            context_parts.append(f"SQL: {q['sql_query']}")
            if q['tables']:
                context_parts.append(f"Tables: {', '.join(q['tables'])}")
            context_parts.append("")
        
        if graph_context:
            context_parts.append("Graph Context (Related usage patterns):")
            context_parts.extend(graph_context)
            context_parts.append("")

        context = "\n".join(context_parts) if context_parts else "No similar queries found."
        
        prompt = f"""
        Based on the following natural language query and similar SQL queries, generate an appropriate SQL query.
        
        Natural Language Query: {query}
        
        Similar SQL Queries and Graph Context for reference:
        {context}
        
        Generate a SQL query that answers the natural language query. Consider:
        1. The table structure inferred from similar queries
        2. Appropriate JOINs if multiple tables are involved
        3. Correct column names and data types
        
        Return your answer as a JSON object with these keys:
        - "sql_query": The generated SQL query
        - "explanation": Brief explanation of the query
        - "tables": List of tables used
        - "columns": List of columns referenced
        
        Only return the JSON object, no additional text.
        """
        
        try:
            response = await self.api_client.get_completion(prompt)
            # Clean response
            cleaned = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            
            # Add metadata
            data["context_queries_used"] = len(context_queries)
            data["original_query"] = query
            data["graph_context_used"] = len(graph_context)
            
            return data
        except Exception as e:
            logger.error(f"Error generating SQL from natural language: {e}")
            return {
                "sql_query": "",
                "explanation": f"Error generating SQL: {str(e)}",
                "tables": [],
                "columns": [],
                "context_queries_used": len(context_queries),
                "original_query": query
            }
    
    async def close(self):
        await self.db.close()
