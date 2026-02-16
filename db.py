import os
import logging
import asyncio
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
from config import settings

# PostgreSQL configuration
PG_HOST = settings.PG_HOST
PG_PORT = settings.PG_PORT
PG_USER = settings.PG_USER
PG_PWD = settings.PG_PWD
PG_DB = settings.PG_DB

# Neo4j configuration
NEO4J_URI = settings.NEO4J_URI
NEO4J_USER = settings.NEO4J_USER
NEO4J_PWD = settings.NEO4J_PWD

import asyncpg
import pgvector.asyncpg
from neo4j import AsyncGraphDatabase
from config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class Database:
    _pg_pool = None
    _neo4j_driver = None

    def __init__(self):
        self.pg_pool = None
        self.neo4j_driver = None

    async def get_pg_pool(self):
        if Database._pg_pool is None:
            try:
                Database._pg_pool = await asyncpg.create_pool(
                    host=settings.PG_HOST,
                    port=settings.PG_PORT,
                    user=settings.PG_USER,
                    password=settings.PG_PWD,
                    database=settings.PG_DB,
                    min_size=1,
                    max_size=10,
                    init=pgvector.asyncpg.register_vector,
                )
                logger.info("Async PostgreSQL pool initialized")
            except Exception as e:
                logger.error(f"Error initializing PG pool: {e}")
                raise
        return Database._pg_pool

    async def get_neo4j_driver(self):
        if Database._neo4j_driver is None:
            try:
                Database._neo4j_driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PWD)
                )
                await Database._neo4j_driver.verify_connectivity()
                logger.info("Async Neo4j driver initialized")
            except Exception as e:
                logger.error(f"Error initializing Neo4j driver: {e}")
                raise
        return Database._neo4j_driver

    async def init_db(self):
        # Initialize PostgreSQL
        pool = await self.get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id SERIAL PRIMARY KEY,
                    content TEXT,
                    metadata JSONB,
                    embedding vector(768) -- adjust dimensions if needed for DeepSeek/OpenAI
                );
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops)"
            )

        # Initialize Neo4j constraints
        driver = await self.get_neo4j_driver()
        async with driver.session() as session:
            # General Entity constraints
            await session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE"
            )
            await session.run("CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            await session.run(
                "CREATE FULLTEXT INDEX entity_names_index IF NOT EXISTS FOR (n:Entity) ON EACH [n.name]"
            )

            # Clinical Specific constraints
            for label, prop in [
                ("Patient", "patientId"),
                ("Doctor", "doctorId"),
                ("Medication", "medicationId"),
                ("Condition", "conditionId"),
                ("Visit", "visitId"),
            ]:
                await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:" + label + ") REQUIRE n." + prop + " IS UNIQUE")  # type: ignore

    async def health_check(self) -> bool:
        """Check health of both PostgreSQL and Neo4j connections."""
        try:
            # Check PostgreSQL
            pool = await self.get_pg_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            # Check Neo4j
            driver = await self.get_neo4j_driver()
            await driver.verify_connectivity()

            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def close(self):
        if Database._pg_pool:
            await Database._pg_pool.close()
        if Database._neo4j_driver:
            await Database._neo4j_driver.close()


if __name__ == "__main__":

    async def main():
        db = Database()
        await db.init_db()
        await db.close()

    asyncio.run(main())
