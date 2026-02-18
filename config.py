"""
Configuration settings for GraphRAG using Pydantic Settings.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL
    PG_HOST: str = "127.0.0.1"
    PG_PORT: str = "5432"
    PG_USER: str = "postgres"
    PG_PWD: Optional[str] = None  # Must be set in .env
    PG_DB: str = "graphrag"

    # Neo4j
    NEO4J_URI: str = "bolt://127.0.0.1:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PWD: Optional[str] = None  # Must be set in .env

    # DeepSeek API
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL_EMBED: str = (
        "sentence-transformers/all-mpnet-base-v2"  # Using local high-quality model (768d)
    )
    DEEPSEEK_MODEL_CHAT: str = "deepseek-chat"
    DEEPSEEK_MODEL_REASONER: str = "deepseek-reasoner"

    # Ingestion settings
    MAX_WORKERS: Optional[int] = None  # default to min(32, cpu_count + 4)
    BATCH_SIZE_EMBEDDINGS: int = 10  # number of texts per embedding batch
    CHUNK_SIZE: int = 500  # docling chunk size (tokens)

    # Search settings
    VECTOR_TOP_K: int = 5
    GRAPH_TOP_K: int = 10
    HYBRID_RERANK: bool = False

    # Paths
    DATA_PATH: str = "data/documents"

    # Security
    ALLOWED_FILE_EXTENSIONS: list[str] = [".pdf", ".docx", ".xlsx", ".csv", ".txt"]
    MAX_UPLOAD_SIZE_MB: int = 100


settings = Settings()
