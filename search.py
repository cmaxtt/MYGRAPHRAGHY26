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
        with conn.cursor() as cur:
            cur.execute("""
                SELECT content FROM chunks 
                ORDER BY embedding <=> %s::vector 
                LIMIT %s
            """, (embedding, top_k))
            rows = cur.fetchall()
            return [row[0] for row in rows]

    def extract_entities(self, query: str) -> List[str]:
        prompt = f"Extract key entities (nouns) from this query. Return as a comma-separated list: {query}"
        response = ollama.generate(model=self.llm_model, prompt=prompt)
        entities = [e.strip() for e in response['response'].split(',')]
        return entities

    def graph_search(self, entities: List[str]) -> List[str]:
        driver = self.db.connect_neo4j()
        results = []
        with driver.session() as session:
            for entity in entities:
                query = """
                MATCH (e:Entity {name: $name})-[r]->(neighbor)
                RETURN e.name as s, type(r) as p, neighbor.name as o
                LIMIT 5
                """
                res = session.run(query, name=entity)
                for record in res:
                    results.append(f"{record['s']} {record['p']} {record['o']}")
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

    def close(self):
        self.db.close()
