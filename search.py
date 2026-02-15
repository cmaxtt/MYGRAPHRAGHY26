import ollama
from db import Database
from typing import List, Dict
import json

class SearchEngine:
    def __init__(self):
        self.db = Database()
        self.embed_model = "nomic-embed-text"
        self.llm_model = "gpt-oss:20b-cloud"

    def hybrid_search(self, query: str, top_k: int = 5) -> Dict:
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
                # Check for clinical labels and Entity labels
                # Deep search: 1-hop and 2-hop for specific labels like Patient -> Visit -> Medication
                query = """
                MATCH (node) 
                WHERE (node:Patient OR node:Doctor OR node:Medication OR node:Condition OR node:Visit OR node:Entity)
                AND (node.name =~ ('(?i).*' + $name + '.*') OR node.patientId = $name OR node.doctorId = $name OR node.visitId = $name)
                
                // 1st level neighbors
                MATCH (node)-[r]-(neighbor)
                
                // Optional 2nd level for Visits (to get prescriptions)
                OPTIONAL MATCH (neighbor)-[r2:PRESCRIBED|TREATED_BY]-(grandchild)
                WHERE neighbor:Visit
                
                RETURN DISTINCT 
                    node.name as s, node.patientId as s_pid, node.visitId as s_vid, node.doctorId as s_did,
                    type(r) as p, 
                    neighbor.name as o, neighbor.patientId as o_pid, neighbor.visitId as o_vid, neighbor.doctorId as o_did,
                    labels(node)[0] as s_label, labels(neighbor)[0] as o_label,
                    type(r2) as p2,
                    grandchild.name as g, grandchild.medicationId as g_mid, labels(grandchild)[0] as g_label
                LIMIT 50
                """
                res = session.run(query, name=entity)
                for record in res:
                    # Format Start Node
                    s_id = record['s_pid'] or record['s_vid'] or record['s_did']
                    s_display = f"{record['s']} [{s_id}]" if record['s'] and s_id else (record['s'] or s_id or "Unknown")
                    
                    # Format Neighbor Node
                    o_id = record['o_pid'] or record['o_vid'] or record['o_did']
                    o_display = f"{record['o']} [{o_id}]" if record['o'] and o_id else (record['o'] or o_id or "Unknown")
                    
                    results.append(f"({s_display}:{record['s_label']}) -[{record['p']}]-> ({o_display}:{record['o_label']})")
                    
                    # Add 2nd hop if exists
                    if record['p2']:
                        g_id = record['g_mid']
                        g_display = f"{record['g']} [{g_id}]" if record['g'] and g_id else (record['g'] or g_id or "Unknown")
                        results.append(f"({o_display}:{record['o_label']}) -[{record['p2']}]-> ({g_display}:{record['g_label']})")
        
        print(f"DEBUG: Found {len(results)} graph relationships for entities {entities}")
        return list(set(results)) # Deduplicate

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
