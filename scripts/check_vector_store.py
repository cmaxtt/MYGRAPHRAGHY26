import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import Database

async def check_vector_store():
    db = Database()
    try:
        pool = await db.get_pg_pool()
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM chunks;")
            print(f"Chunks table row count: {count}")
            if count > 0:
                sample = await conn.fetchrow("SELECT id, content FROM chunks LIMIT 1;")
                if sample:
                    print(f"Sample chunk ID: {sample['id']}, content preview: {sample['content'][:100]}...")
    except Exception as e:
        print(f"Error checking PostgreSQL: {e}")
    finally:
        await db.close()

def main():
    asyncio.run(check_vector_store())

if __name__ == "__main__":
    main()