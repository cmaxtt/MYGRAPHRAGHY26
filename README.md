# Local Hybrid GraphRAG System

A local implementation of GraphRAG using Docling, Neo4j, PostgreSQL (pgvector), and Ollama.

## Setup Instructions

1.  **Docker**: Ensure Docker Desktop is running.
2.  **Ollama**: Ensure Ollama is running and models are pulled:
    ```bash
    ollama pull gpt-oss:20b-cloud
    ollama pull nomic-embed-text
    ```
3.  **Environment**:
    ```bash
    pip install -r requirements.txt
    docker-compose up -d
    python db.py  # Initialize schemas
    ```
4.  **Run**:
    ```bash
    streamlit run app.py
    ```

## Database Resets

If you need to clear the data:

### PostgreSQL (Vector Data)
```sql
docker exec -it mygraphrag-postgres-1 psql -U postgres -d graphrag -c "TRUNCATE TABLE chunks;"
```

### Neo4j (Graph Data)
Login to `http://localhost:7474` (neo4j/password) and run:
```cypher
MATCH (n) DETACH DELETE n;
```

Alternatively, wipe volumes:
```bash
bash docker-compose down -v
docker-compose up -d
python db.py
```

