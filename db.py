import os
import logging
import asyncio
import time
from dotenv import load_dotenv
import asyncpg
import pgvector.asyncpg
from neo4j import AsyncGraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
from config import settings

class Database:
    # Dictionary to hold pools/drivers for each event loop
    # Maps loop_id -> pool_instance
    _pg_pools = {}
    _neo4j_drivers = {}

    def __init__(self):
        # We don't store instances locally anymore, we rely on the class-level registry 
        # keyed by the event loop.
        pass

    async def get_pg_pool(self) -> asyncpg.Pool:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
            
        loop_id = id(loop)
        
        # Check if pool exists and is not closing
        pool = Database._pg_pools.get(loop_id)
        if pool and pool.is_closing():
            pool = None
            
        if not pool:
            try:
                Database._pg_pools[loop_id] = await asyncpg.create_pool(
                    host=settings.PG_HOST,
                    port=settings.PG_PORT,
                    user=settings.PG_USER,
                    password=settings.PG_PWD,
                    database=settings.PG_DB,
                    min_size=1,
                    max_size=10,
                    init=pgvector.asyncpg.register_vector,
                )
                logger.info(f"Async PostgreSQL pool initialized for loop {loop_id}")
            except Exception as e:
                logger.error(f"Error initializing PG pool: {e}")
                raise
        return Database._pg_pools[loop_id]

    async def get_neo4j_driver(self) -> any:  # Neo4j driver type is complex to import if not available
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
            
        loop_id = id(loop)
        
        if loop_id not in Database._neo4j_drivers:
            try:
                # Create driver
                driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PWD)
                )
                await driver.verify_connectivity()
                Database._neo4j_drivers[loop_id] = driver
                logger.info(f"Async Neo4j driver initialized for loop {loop_id}")
            except Exception as e:
                logger.error(f"Error initializing Neo4j driver: {e}")
                raise
        return Database._neo4j_drivers[loop_id]

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

            # Create query_embeddings table for SQL query retrieval
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS query_embeddings (
                    id BIGSERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    description TEXT,
                    sql_query TEXT NOT NULL,
                    query_type VARCHAR(50),
                    associated_tables TEXT[],
                    table_links JSONB,
                    used_columns JSONB,
                    database_schema TEXT DEFAULT 'public',
                    version INTEGER NOT NULL DEFAULT 1,
                    is_active BOOLEAN DEFAULT true,
                    superseded_by BIGINT REFERENCES query_embeddings(id),
                    embedding vector(768) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # Create indexes for query_embeddings
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_query_embeddings_type ON query_embeddings(query_type);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_query_embeddings_tables ON query_embeddings USING GIN(associated_tables);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_query_embeddings_links ON query_embeddings USING GIN(table_links);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_query_embeddings_active ON query_embeddings(is_active);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_query_embeddings_embedding_hnsw ON query_embeddings USING hnsw (embedding vector_cosine_ops);")

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

            # SQL RAG Constraints
            for label in ["Query", "Table", "Column"]:
                await session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE")




    async def insert_query_embedding(self, question, sql_query, embedding, description=None, query_type=None,
                                     associated_tables=None, table_links=None, used_columns=None,
                                     database_schema='public'):
        """Insert a new query embedding with metadata."""
        import json
        pool = await self.get_pg_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval("""
                INSERT INTO query_embeddings 
                (question, sql_query, embedding, description, query_type, associated_tables, 
                 table_links, used_columns, database_schema)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """, question, sql_query, embedding, description, query_type, associated_tables,
                 json.dumps(table_links) if table_links is not None else None,
                 json.dumps(used_columns) if used_columns is not None else None,
                 database_schema)

    async def search_query_embeddings(self, embedding, limit=5, query_type=None, tables=None):
        """Search for similar SQL queries using vector similarity and optional filters."""
        pool = await self.get_pg_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT id, question, sql_query, associated_tables, table_links,
                       1 - (embedding <=> $1) as similarity
                FROM query_embeddings
                WHERE is_active = true
            """
            params = [embedding]
            param_idx = 2
            
            if query_type:
                query += f" AND query_type = ${param_idx}"
                params.append(query_type)
                param_idx += 1
            
            if tables:
                query += f" AND associated_tables && ${param_idx}"
                params.append(tables)
                param_idx += 1
            
            query += f" ORDER BY embedding <=> $1 LIMIT ${param_idx}"
            params.append(limit)
            
            return await conn.fetch(query, *params)

    async def get_query_by_id(self, query_id):
        """Retrieve a query embedding by ID."""
        pool = await self.get_pg_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM query_embeddings WHERE id = $1",
                query_id
            )

    async def deactivate_query(self, query_id):
        """Soft delete a query by setting is_active = false."""
        pool = await self.get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE query_embeddings SET is_active = false WHERE id = $1",
                query_id
            )

    async def update_query_version(self, old_query_id, new_question, new_sql_query, 
                                   new_embedding, description=None, query_type=None,
                                   associated_tables=None, table_links=None, used_columns=None):
        """Create a new version of a query, superseding the old one."""
        import json
        pool = await self.get_pg_pool()
        async with pool.acquire() as conn:
            # Get old query to copy some metadata
            old_query = await self.get_query_by_id(old_query_id)
            if not old_query:
                raise ValueError(f"Query with ID {old_query_id} not found")
            
            # Insert new version
            new_id = await conn.fetchval("""
                INSERT INTO query_embeddings 
                (question, description, sql_query, query_type, associated_tables,
                 table_links, used_columns, database_schema, embedding, version)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            """, new_question, description or old_query['description'],
               new_sql_query, query_type or old_query['query_type'],
               associated_tables or old_query['associated_tables'],
               json.dumps(table_links or old_query['table_links']) if (table_links or old_query['table_links']) is not None else None,
               json.dumps(used_columns or old_query['used_columns']) if (used_columns or old_query['used_columns']) is not None else None,
               old_query['database_schema'], new_embedding,
               old_query['version'] + 1)
            
            # Deactivate old query and link to new version
            await conn.execute("""
                UPDATE query_embeddings 
                SET is_active = false, superseded_by = $1
                WHERE id = $2
            """, new_id, old_query_id)
            
            return new_id

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
        # Close all pools/drivers
        for pool in Database._pg_pools.values():
            await pool.close()
        Database._pg_pools.clear()
        
        for driver in Database._neo4j_drivers.values():
            await driver.close()
        Database._neo4j_drivers.clear()


if __name__ == "__main__":

    async def main():
        db = Database()
        await db.init_db()
        await db.close()

    asyncio.run(main())
