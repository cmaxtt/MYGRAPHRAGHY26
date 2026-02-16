# 🌐 CompuMax Local Hybrid GraphRAG System 2025

A high-performance, privacy-focused **Graph Retrieval-Augmented Generation (GraphRAG)** system that combines the power of **Vector Search** with the contextual richness of **Knowledge Graphs**. Built to run entirely locally, keeping your data secure.

![GraphRAG Architecture](https://img.shields.io/badge/Architecture-Hybrid%20Graph%20%2B%20Vector-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![License](https://img.shields.io/badge/License-MIT-purple)

## 🚀 Key Features

*   **Hybrid Search Engine**: Synergizes **pgvector** (PostgreSQL) for semantic similarity and **Neo4j** for graph traversals to answer complex queries.
*   **Efficient & Scalable**: Uses **DeepSeek API** for LLM reasoning and **local SentenceTransformer** for embeddings, balancing performance and privacy.
*   **Multi-Modal Ingestion**: 
    *   **Clinical Data**: specialized ingestion for CSV patient records, doctor interactions, and prescriptions.
    *   **Document Uploads**: Support for PDF, DOCX, XLSX, CSV, and TXT files via the Web UI.
*   **Interactive UI**: A polished **Streamlit** interface offering:
    *   Real-time chat with citation of sources (Vector vs. Graph nodes).
    *   Dynamic **Knowledge Graph Visualization**.
    *   System health metrics and database stats.
*   **Advanced Entity Extraction**: Automatically identifies people, medications, conditions, and IDs to construct a rich knowledge graph.

---

## 🏗️ Architecture

1.  **Ingestion Layer**: 
    *   Documents are parsed and chunked.
    *   **Vector Path**: Chunks are embedded using `nomic-embed-text` and stored in **PostgreSQL**.
    *   **Graph Path**: Entities and relationships are extracted using an LLM and stored in **Neo4j**.
2.  **Retrieval Layer**:
    *   **Vector Search**: Finds conceptually similar text chunks.
    *   **Graph Search**: Traverses the graph to find related entities (e.g., "What side effects does the medication prescribed to Patient X have?").
3.  **Generation Layer**:
    *   The LLM (`gpt-oss:20b-cloud` or configured model) synthesizes the answer using context from both sources.

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

### Ingesting Clinical Demo Data
To populate the graph with the provided sample clinical dataset (Patients, Doctors, Medications):
```bash
python ingest_clinical.py
```

### Using the UI
1.  **Chat Tab**: Ask questions like "Who is Dr. Smith treating?" or "What are the side effects of Metformin?".
2.  **Knowledge Graph Tab**: Visualize the nodes and edges created from your data.
3.  **Sidebar**: Upload your own documents (PDF, TXT, etc.) to expand the knowledge base.

---

## 📂 Project Structure

```
.
├── app.py                  # Main Streamlit Web Application
├── config.py               # Central configuration (env vars, constants)
├── db.py                   # Database connection manager (Neo4j & Postgres)
├── ingest.py               # Generic document ingestor
├── ingest_clinical.py      # Specialized clinical CSV ingestor
├── search.py               # Hybrid search engine logic
├── base_ingestor.py        # Base class for ingestion strategies
├── docker-compose.yml      # Container definition for DBs
├── requirements.txt        # Python dependencies
├── data/
│   └── clinical/           # Sample CSV datasets
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
