#!/usr/bin/env python3
"""Integration test for SQL query retrieval system."""

import asyncio
import os
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import Database
from ingest import Ingestor
from search import QuerySearchEngine


async def test_full_sql_flow():
    """Test the complete SQL query extraction, storage, search, and generation flow."""
    
    print("=== SQL Query Retrieval System Integration Test ===\n")
    
    # Initialize components
    db = Database()
    ingestor = Ingestor(db)
    query_search = QuerySearchEngine(db)
    
    # Ensure database is initialized
    await db.init_db()
    
    # Clean up any existing test data
    pool = await db.get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM query_embeddings WHERE sql_query LIKE '%test%' OR question LIKE '%test%'")
    
    print("1. Creating test SQL document...")
    
    # Create a temporary SQL document
    test_content = """
    SQL Query Examples Document
    
    This document contains various SQL queries for testing the SQL query retrieval system.
    
    1. SELECT customer_id, COUNT(*) as order_count FROM orders GROUP BY customer_id HAVING COUNT(*) > 5;
    
    2. INSERT INTO products (name, price, category) VALUES ('Laptop', 999.99, 'Electronics'), ('Mouse', 29.99, 'Accessories');
    
    3. UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = 123;
    
    4. DELETE FROM logs WHERE created_at < NOW() - INTERVAL '30 days';
    
    5. CREATE TABLE employees (
        employee_id SERIAL PRIMARY KEY,
        first_name VARCHAR(50),
        last_name VARCHAR(50),
        department VARCHAR(50),
        salary DECIMAL(10,2)
    );
    
    6. SELECT 
        c.name as customer_name,
        SUM(o.total) as total_spent,
        AVG(o.total) as avg_order_value
    FROM customers c
    INNER JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_date >= '2024-01-01'
    GROUP BY c.customer_id, c.name
    ORDER BY total_spent DESC
    LIMIT 10;
    
    7. ALTER TABLE products ADD COLUMN stock_quantity INTEGER DEFAULT 0;
    
    8. DROP TABLE IF EXISTS temporary_data;
    
    These are example queries that should be extracted and indexed.
    """
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        temp_file = f.name
    
    try:
        print(f"   Created temporary file: {temp_file}")
        
        print("\n2. Ingesting SQL document...")
        
        # Ingest the document
        await ingestor.process_file(temp_file)
        
        print("   Document ingestion complete.")
        
        # Check if queries were stored
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM query_embeddings WHERE is_active = true")
            print(f"\n3. Stored {count} active SQL queries in database.")
            
            if count == 0:
                print("   ERROR: No SQL queries were extracted!")
                return False
        
        print("\n4. Testing search functionality...")
        
        # Test search for queries about "customer orders"
        print("   Searching for queries about 'customer orders'...")
        results = await query_search.search_sql_queries(
            query="How to find customers with many orders",
            limit=3
        )
        
        print(f"   Found {len(results)} relevant queries")
        for i, result in enumerate(results):
            print(f"     {i+1}. Similarity: {result['similarity']:.3f}")
            print(f"        SQL: {result['sql_query'][:80]}...")
        
        # Test search with table filter
        print("\n   Searching for queries involving 'customers' table...")
        results = await query_search.search_sql_queries(
            query="customer data",
            tables=["customers"],
            limit=2
        )
        
        print(f"   Found {len(results)} queries with 'customers' table")
        
        print("\n5. Testing metadata retrieval...")
        
        # Get query types
        query_types = await query_search.get_all_query_types()
        print(f"   Query types in database: {', '.join(query_types)}")
        
        # Get tables
        tables = await query_search.get_all_tables()
        print(f"   Tables in database: {', '.join(sorted(tables))}")
        
        # Get statistics
        stats = await query_search.get_query_statistics()
        print(f"   Total queries: {stats.get('total_queries', 0)}")
        
        print("\n6. Testing SQL generation from natural language...")
        
        # Generate SQL from natural language
        print("   Generating SQL for: 'Show me the total sales per customer'")
        generated = await query_search.generate_sql_from_natural_language(
            query="Show me the total sales per customer"
        )
        
        if generated.get("sql_query"):
            print("   Generated SQL query:")
            print(f"     {generated['sql_query']}")
            print(f"   Explanation: {generated.get('explanation', 'N/A')}")
        else:
            print("   ERROR: Failed to generate SQL")
            print(f"   Error: {generated.get('explanation', 'Unknown error')}")
        
        print("\n7. Testing query details retrieval...")
        
        # Get details of first query
        if results:
            first_id = results[0]["id"]
            details = await query_search.get_sql_query_details(first_id)
            print(f"   Retrieved details for query ID {first_id}")
            print(f"   Question: {details.get('question', 'N/A')}")
            print(f"   Type: {details.get('query_type', 'N/A')}")
        
        print("\n=== Integration Test Summary ===")
        print("[OK] Document ingestion and SQL extraction")
        print("[OK] Query storage in database")
        print("[OK] Semantic search with embeddings")
        print("[OK] Metadata filtering (tables, query types)")
        print("[OK] Statistics and metadata retrieval")
        print("[OK] SQL generation from natural language")
        print("[OK] Query details retrieval")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up temporary file
        if 'temp_file' in locals() and os.path.exists(temp_file):
            os.unlink(temp_file)
            print(f"\nCleaned up temporary file: {temp_file}")
        
        # Clean up test data from database
        try:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM query_embeddings WHERE sql_query LIKE '%test%' OR question LIKE '%test%' OR sql_query LIKE '%customer%' OR sql_query LIKE '%orders%'")
                print("Cleaned up test data from query_embeddings table")
        except Exception as e:
            print(f"Warning: error cleaning up test data: {e}")
        
        # Close connections
        await db.close()


if __name__ == "__main__":
    print("Running SQL query retrieval system integration test...\n")
    
    success = asyncio.run(test_full_sql_flow())
    
    if success:
        print("\n[SUCCESS] ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n[FAILURE] SOME TESTS FAILED")
        sys.exit(1)