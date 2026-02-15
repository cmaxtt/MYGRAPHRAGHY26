import ollama
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

from db import Database
from config import settings
from typing import List, Dict
import json

class SearchEngine:
    def __init__(self, db=None):
        self.db = db or Database()
        self.embed_model = settings.EMBED_MODEL
        self.llm_model = settings.LLM_MODEL

    def hybrid_search(self, query: str, top_k: int = settings.VECTOR_TOP_K) -> Dict:
        # 1. Vector Search
        query_embedding = self.get_embedding(query)
        vector_results = self.vector_search(query_embedding, top_k)
        
        # 2. Extract Entities for Graph Search
        entities = self.extract_entities(query)
        graph_results = self.graph_search(entities)
        
        # 3. Combine Context
        context = "### Vector Context:\n"
        for res in vector_results:
            context += f"- {res}\n"
        
        context += "\n### Graph Context:\n"
        for res in graph_results:
            context += f"- {res}\n"
            
        # 4. Generate Answer
        answer = self.generate_answer(query, context)
        
        return {
            "answer": answer,
            "sources": {
                "vector_count": len(vector_results),
                "graph_count": len(graph_results),
                "entities_found": entities
            }
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_embedding(self, text: str) -> List[float]:
        response = ollama.embeddings(model=self.embed_model, prompt=text)
        return response['embedding']

    def vector_search(self, embedding: List[float], top_k: int) -> List[str]:
        conn = self.db.connect_pg()
        if not conn: return []
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT content FROM chunks 
                    ORDER BY embedding <=> %s::vector 
                    LIMIT %s
                """, (embedding, top_k))
                rows = cur.fetchall()
                return [row[0] for row in rows]
        finally:
            self.db.release_pg(conn)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def extract_entities(self, query: str) -> List[str]:
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
        response = ollama.generate(model=self.llm_model, prompt=prompt)
        entities = [e.strip() for e in response['response'].split(',') if len(e.strip()) > 1]
        return entities[:8] # Increased limit slightly

    def graph_search(self, entities: List[str]) -> List[str]:
        driver = self.db.connect_neo4j()
        results = []
        with driver.session() as session:
            for entity in entities:
                # Optimized search using the unified Entity label
                # We look for nodes with the Entity label that match the name or ID
                query = """
                MATCH (node:Entity) 
                WHERE (node.name =~ ('(?i).*' + $name + '.*') OR node.patientId = $name OR node.doctorId = $name OR node.visitId = $name)
                
                // 1st level neighbors
                MATCH (node)-[r]-(neighbor:Entity)
                
                // Optional 2nd level for Visits (to get prescriptions/treatments) - specific to clinical flow but generic enough
                OPTIONAL MATCH (neighbor)-[r2:PRESCRIBED|TREATED_BY]-(grandchild:Entity)
                WHERE neighbor:Visit
                
                RETURN DISTINCT 
                    node.name as s, 
                    type(r) as p, 
                    neighbor.name as o, 
                    labels(node) as s_labels, labels(neighbor) as o_labels,
                    type(r2) as p2,
                    grandchild.name as g, labels(grandchild) as g_labels
                LIMIT 50
                """
                try:
                    res = session.run(query, name=entity)
                    for record in res:
                        # Helper to get the most specific label (filtering out 'Entity')
                        def get_label(labels):
                            return next((l for l in labels if l != 'Entity'), 'Entity')

                        s_label = get_label(record['s_labels'])
                        o_label = get_label(record['o_labels'])
                        
                        s_name = record['s'] or "Unknown"
                        o_name = record['o'] or "Unknown"

                        results.append(f"({s_name}:{s_label}) -[{record['p']}]-> ({o_name}:{o_label})")
                        
                        # Add 2nd hop if exists
                        if record['p2']:
                            g_label = get_label(record['g_labels'])
                            g_name = record['g'] or "Unknown"
                            results.append(f"({o_name}:{o_label}) -[{record['p2']}]-> ({g_name}:{g_label})")
                except Exception as e:
                    logger.error(f"Error in graph search for entity '{entity}': {e}")
        
        logger.info(f"DEBUG: Found {len(results)} graph relationships for entities {entities}")
        return list(set(results)) # Deduplicate

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_answer(self, query: str, context: str) -> str:
        prompt = f"""
        You are a helpful assistant. Use the following context to answer the user query.
        If the context does not contain enough information, say so.
        
        Context:
        {context}
        
        User Query: {query}
        """
        response = ollama.generate(model=self.llm_model, prompt=prompt)
        return response['response']

    def get_all_graph_data(self):
        driver = self.db.connect_neo4j()
        nodes = []
        edges = []
        with driver.session() as session:
            # Get nodes
            node_query = "MATCH (n:Entity) RETURN n.name as id, n.name as label, labels(n)[0] as type LIMIT 100"
            node_res = session.run(node_query)
            for record in node_res:
                nodes.append({
                    "id": record["id"],
                    "label": record["label"],
                    "type": record["type"]
                })
            
            # Get edges
            edge_query = "MATCH (s:Entity)-[r]->(o:Entity) RETURN s.name as source, type(r) as label, o.name as target LIMIT 100"
            edge_res = session.run(edge_query)
            for record in edge_res:
                edges.append({
                    "source": record["source"],
                    "label": record["label"],
                    "target": record["target"]
                })
        return nodes, edges

    def close(self):
        self.db.close()
