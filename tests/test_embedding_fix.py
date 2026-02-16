import asyncio
import sys
sys.path.insert(0, '.')
from api_client import api_client

async def test():
    texts = ["Hello world", "Test embedding"]
    embeddings = await api_client.get_embeddings(texts)
    print(f"Number of embeddings: {len(embeddings)}")
    for i, emb in enumerate(embeddings):
        print(f"Embedding {i} length: {len(emb)}")
        print(f"First few values: {emb[:5]}")
        print(f"Type: {type(emb)}")
        assert isinstance(emb, list), "Embedding should be a list"
        assert all(isinstance(x, float) for x in emb), "All elements should be floats"
    print("Test passed")

if __name__ == "__main__":
    asyncio.run(test())