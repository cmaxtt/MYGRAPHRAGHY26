import logging
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import List, Dict
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
        - People (e.g., Sarah Singh)
        - Identifiers (e.g., P20, V72, D1)
        - Medications (e.g., Tamoxifen)
        - Conditions (e.g., Type 2 Diabetes)
        
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
                  WHERE matchedNode.patientId = searchTerm 
                     OR matchedNode.doctorId = searchTerm 
                     OR matchedNode.visitId = searchTerm
                  RETURN matchedNode
                  LIMIT 5
                }
                WITH DISTINCT matchedNode
                MATCH (matchedNode)-[r]-(neighbor:Entity)
                
                // Optional 2nd level for Visits
                OPTIONAL MATCH (neighbor)-[r2:PRESCRIBED|TREATED_BY]-(grandchild:Entity)
                WHERE neighbor:Visit
                
                RETURN DISTINCT 
                    matchedNode.name as s, 
                    type(r) as p, 
                    neighbor.name as o, 
                    labels(matchedNode) as s_labels, labels(neighbor) as o_labels,
                    type(r2) as p2,
                    grandchild.name as g, labels(grandchild) as g_labels
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

                        if record["p2"]:
                            g_label = get_label(record["g_labels"])
                            g_name = record["g"] or "Unknown"
                            results.append(
                                f"({o_name}:{o_label}) -[{record['p2']}]-> ({g_name}:{g_label})"
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
        You are a helpful clinical assistant. 
        Use the provided context to answer the user query accurately.
        If the context is insufficient, state that clearly.
        Maintain patient privacy and professional tone.
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
