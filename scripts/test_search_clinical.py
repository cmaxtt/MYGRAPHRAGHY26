import sys
import os
import json
import io

# Fix encoding issues for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from search import SearchEngine

def test_search():
    engine = SearchEngine()
    query = "Explain Dr. Samuel Peters' reasoning for treating Sarah Singh with Tamoxifen."
    print(f"Query: {query}")
    
    result = engine.hybrid_search(query)
    
    print("\n--- Answer ---")
    print(result["answer"])
    print("\n--- Sources ---")
    print(f"Entities found: {result['sources']['entities_found']}")
    print(f"Vector chunks: {result['sources']['vector_count']}")
    print(f"Graph relationships: {result['sources']['graph_count']}")
    
    engine.close()

if __name__ == "__main__":
    test_search()
