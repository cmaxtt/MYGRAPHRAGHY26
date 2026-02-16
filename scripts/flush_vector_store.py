"""
Flush/clear all data from PostgreSQL vector store.
"""
import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import Database

async def flush_vector_store():
    """Delete all data from vector store tables."""
    db = Database()
    try:
        pool = await db.get_pg_pool()
        async with pool.acquire() as conn:
            # Delete all rows from chunks table
            deleted = await conn.execute("DELETE FROM chunks;")
            print(f"Deleted {deleted.split()[1]} rows from chunks table")
            
            # Reset the serial sequence (id) to start from 1
            await conn.execute("ALTER SEQUENCE chunks_id_seq RESTART WITH 1;")
            print("Reset chunks_id_seq sequence")
            
            # Optional: Vacuum to reclaim space
            # await conn.execute("VACUUM;")
            # print("Vacuum completed")
            
            # Verify deletion
            count = await conn.fetchval("SELECT COUNT(*) FROM chunks;")
            print(f"Verified: chunks table now has {count} rows")
            
    except Exception as e:
        print(f"Error flushing vector store: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

def main():
    print("Flushing PostgreSQL vector store...")
    asyncio.run(flush_vector_store())
    print("Flush completed.")

if __name__ == "__main__":
    main()