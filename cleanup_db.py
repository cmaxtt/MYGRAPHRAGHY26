import asyncio
import logging
from db import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cleanup_db")

async def cleanup():
    logger.info("Starting database cleanup...")
    db = Database()
    
    # 1. Clear PostgreSQL (Vector Store)
    try:
        pool = await db.get_pg_pool()
        async with pool.acquire() as conn:
            logger.info("Clearing PostgreSQL tables (chunks, query_embeddings)...")
            # Truncate tables with CASCADE to handle foreign key constraints
            await conn.execute("TRUNCATE TABLE chunks, query_embeddings CASCADE;")
            logger.info("PostgreSQL tables cleared successfully.")
    except Exception as e:
        logger.error(f"Error clearing PostgreSQL: {e}")

    # 2. Clear Neo4j (Graph Store)
    try:
        driver = await db.get_neo4j_driver()
        async with driver.session() as session:
            logger.info("Clearing Neo4j graph data...")
            # Delete all nodes and relationships
            await session.run("MATCH (n) DETACH DELETE n")
            logger.info("Neo4j graph cleared successfully.")
    except Exception as e:
        logger.error(f"Error clearing Neo4j: {e}")

    # Close connections
    await db.close()
    logger.info("Cleanup completed.")

if __name__ == "__main__":
    asyncio.run(cleanup())
