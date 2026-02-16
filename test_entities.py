import asyncio
import sys
sys.path.insert(0, '.')
from api_client import api_client

async def test():
    prompt = """
        Extract the most important specific entities from the following query.
        Look for:
        - People (e.g., Sarah Singh)
        - Identifiers (e.g., P20, V72, D1)
        - Medications (e.g., Tamoxifen)
        - Conditions (e.g., Type 2 Diabetes)
        
        Return ONLY a comma-separated list of names or IDs. No extra text.
        Query: Who is Dr. Smith treating?
        """
    response = await api_client.get_reasoning(prompt)
    print(f"Response: {response}")
    entities = [e.strip() for e in response.strip().split(',') if len(e.strip()) > 1]
    print(f"Entities: {entities}")

if __name__ == "__main__":
    asyncio.run(test())