
import asyncio
import os
from dotenv import load_dotenv
from api_client import api_client

load_dotenv()

async def reproduce():
    print("Testing embedding generation...")
    try:
        embedding = await api_client.get_embeddings(["Test query P20"])
        print(f"Success. Embedding len: {len(embedding[0])}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reproduce())
