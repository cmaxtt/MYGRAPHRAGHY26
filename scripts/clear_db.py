import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import Database

async def clear_and_reinit():
    db = Database()
    
    # 1. Clear Neo4j
    print("Clearing Neo4j data...")
    try:
        driver = await db.get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run("MATCH (n) DETACH DELETE n")
            summary = await result.consume()
            print(f"  Neo4j cleanup: Deleted {summary.counters.nodes_deleted} nodes and {summary.counters.relationships_deleted} relationships.")
    except Exception as e:
        print(f"Error clearing Neo4j: {e}")

    # 2. Clear PostgreSQL
    print("Clearing PostgreSQL data...")
    try:
        pool = await db.get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE chunks RESTART IDENTITY;")
            print("  PostgreSQL cleanup: Table 'chunks' truncated and identity reset.")
    except Exception as e:
        print(f"Error clearing PostgreSQL: {e}")

    # Reinitialize database (ensure tables and constraints)
    print("Reinitializing database...")
    await db.init_db()
    print("Database reinitialized.")
    
    await db.close()
    print("Database cleanup complete.")

def main():
    asyncio.run(clear_and_reinit())

if __name__ == "__main__":
    main()
