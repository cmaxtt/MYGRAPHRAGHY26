
import asyncio
import os
import traceback
from dotenv import load_dotenv
from search import SearchEngine

load_dotenv()

async def reproduce_search():
    print("Testing hybrid search...")
    search_engine = SearchEngine()
    try:
        result = await search_engine.hybrid_search("What is the status of P20?")
        print("Success!")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reproduce_search())
