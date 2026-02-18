# 🌐 CompuMax Local Hybrid GraphRAG System 2026

A high-performance, privacy-focused **Graph Retrieval-Augmented Generation (GraphRAG)** system that combines the power of **Vector Search** with the contextual richness of **Knowledge Graphs**. Built to run entirely locally, keeping your data secure.

![GraphRAG Architecture](https://img.shields.io/badge/Architecture-Hybrid%20Graph%20%2B%20Vector-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![License](https://img.shields.io/badge/License-MIT-purple)

## 🚀 Key Features

*   **Hybrid Search Engine**: Synergizes **pgvector** (PostgreSQL) for semantic similarity and **Neo4j** for graph traversals to answer complex queries.
*   **Text-to-SQL Interface**:  *New!*  Translates natural language questions into accurate SQL queries using a hybrid RAG approach (Vector + Graph) to understand database schema and usage patterns.
*   **Efficient & Scalable**: Uses **DeepSeek API** for LLM reasoning and **local SentenceTransformer** for embeddings, balancing performance and privacy.
*   **Multi-Modal Ingestion**: 
    *   **Document Uploads**: Support for PDF, DOCX, XLSX, CSV, and TXT files via the Web UI.
    *   **SQL Training Data**: Ingest CSVs of natural language queries and their corresponding SQL to train the system.
*   **Interactive UI**: A polished **Streamlit** interface offering:
    *   Real-time chat with citation of sources (Vector vs. Graph nodes).
    *   **SQL Query Tab**:  Execute natural language queries against your data.
    *   Dynamic **Knowledge Graph Visualization**.
    *   System health metrics and database stats.
*   **Advanced Entity Extraction**: Automatically identifies key entities and concepts to construct a rich knowledge graph.

---

## 🏗️ Architecture

1.  **Ingestion Layer**: 
    *   **Documents**: Parsed and chunked.
    *   **SQL Data**: Natural language queries are embedded (Vector) and parsed into Query/Table/Column nodes (Graph).
    *   **Vector Path**: Chunks/Queries are embedded using `nomic-embed-text` and stored in **PostgreSQL**.
    *   **Graph Path**: Entities/Tables and relationships are extracted/parsed and stored in **Neo4j**.
2.  **Retrieval Layer**:
    *   **Vector Search**: Finds conceptually similar text chunks or past SQL queries.
    *   **Graph Search**: Traverses the graph to find related entities, relationships, or table usage patterns.
3.  **Generation Layer**:
    *   The LLM (`deepseek-chat` or `deepseek-reasoner`) synthesizes the answer or generates SQL using context from both sources.

---

## 🛠️ Prerequisites

Ensure you have the following installed:

*   **Docker Desktop** (for PostgreSQL and Neo4j)
*   **Python 3.10+**
*   **DeepSeek API Key** (get from [DeepSeek Platform](https://platform.deepseek.com))

---

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/cmaxtt/MYGRAPHRAG.git
cd MYGRAPHRAG
```

### 2. Set Up Environment
Create a `.env` file from the example:
```bash
cp .env.example .env
```
*Edit `.env` to set your DeepSeek API key and database credentials.*

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start Database Services
Launch PostgreSQL and Neo4j using Docker Compose:
```bash
docker-compose up -d
```

### 5. Initialize Databases
Create the necessary schemas and indexes:
```bash
python db.py
```

### 6. Configure API Key
Ensure your DeepSeek API key is set in `.env`. The embedding model (SentenceTransformer) will download automatically on first use.

---

## 🖥️ Usage

### Running the Web Application
Launch the Streamlit interface:
```bash
streamlit run app.py
```
Access the app at `http://localhost:8501`.

### Using the UI
1.  **Chat Tab**: Ask questions about your documents (unstructured data).
2.  **SQL Query Tab**: Ask questions about your structured data (e.g., "Show me top customers by sales").
3.  **Knowledge Graph Tab**: Visualize the nodes and edges created from your data.
4.  **Sidebar**: Upload your own documents (PDF, TXT, etc.) to expand the knowledge base.

### Ingesting SQL Training Data
To teach the system about your database schema and common queries, prepare a CSV file (e.g., `data/training_data.csv`) with `natural_language_query` and `sql_query` columns, then run:

```bash
python -m ingestion.sql_ingestor
```

---

## 📂 Project Structure

```
.
├── app.py                  # Main Streamlit Web Application
├── config.py               # Central configuration (env vars, constants)
├── db.py                   # Database connection manager (Neo4j & Postgres)
├── ingest.py               # Generic document ingestor
├── ingestion/
│   └── sql_ingestor.py     # SQL training data ingestor
├── search.py               # Hybrid search engine logic (Chat & SQL)
├── base_ingestor.py        # Base class for ingestion strategies
├── docker-compose.yml      # Container definition for DBs
├── requirements.txt        # Python dependencies
├── data/
│   └── training_data.csv   # Example SQL training data
└── scripts/                # Utility scripts
```

## ⚙️ Configuration

The `config.py` file controls the system behavior. Key settings include:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DEEPSEEK_MODEL_CHAT` | Model for chat completion | `deepseek-chat` |
| `DEEPSEEK_MODEL_REASONER` | Model for reasoning tasks | `deepseek-reasoner` |
| `DEEPSEEK_MODEL_EMBED` | Local embedding model | `sentence-transformers/all-mpnet-base-v2` |
| `VECTOR_TOP_K` | Number of vector chunks to retrieve | `5` |
| `GRAPH_TOP_K` | Number of graph entities to explore | `10` |
| `PG_HOST` | PostgreSQL Host | `127.0.0.1` |
| `NEO4J_URI` | Neo4j Connection URI | `bolt://127.0.0.1:7687` |

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

---

*Verified by CompuMax Agentic Coding Team*
