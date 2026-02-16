#!/usr/bin/env python3
"""Test SQL query extraction from documents."""

import asyncio
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import Database
from ingest import Ingestor


async def test_sql_extraction_direct():
    """Test SQL query extraction directly with text input."""
    
    print("Testing SQL query extraction...")
    
    # Initialize ingestor and database
    db = Database()
    ingestor = Ingestor(db)
    
    # Ensure database is initialized
    await db.init_db()
    
    # Check initial count of query_embeddings
    pool = await db.get_pg_pool()
    async with pool.acquire() as conn:
        initial_count = await conn.fetchval("SELECT COUNT(*) FROM query_embeddings")
        print(f"Initial query_embeddings count: {initial_count}")
    
    # Test text with SQL queries
    test_text = """
    Here are some example SQL queries:
    
    1. SELECT customer_id, SUM(amount) FROM sales GROUP BY customer_id;
    
    2. INSERT INTO users (username, email) VALUES ('test', 'test@example.com');
    
    3. CREATE TABLE products (id SERIAL PRIMARY KEY, name TEXT, price DECIMAL);
    """
    
    try:
        # Extract SQL queries using LLM
        print("Extracting SQL queries from text...")
        sql_queries = await ingestor.extract_sql_queries(test_text)
        
        print(f"Extracted {len(sql_queries)} SQL queries")
        for i, q in enumerate(sql_queries):
            print(f"  Query {i+1}:")
            print(f"    SQL: {q.get('sql_query', 'N/A')[:100]}...")
            print(f"    Type: {q.get('query_type', 'N/A')}")
            print(f"    Tables: {q.get('tables', [])}")
            print(f"    Columns: {q.get('columns', [])}")
        
        if len(sql_queries) == 0:
            print("WARNING: No SQL queries extracted. LLM may have returned empty list.")
            # Try with simpler text
            simple_text = "SELECT * FROM users;"
            sql_queries = await ingestor.extract_sql_queries(simple_text)
            print(f"Simple extraction: {len(sql_queries)} queries")
        
        # Store extracted queries
        print("\nStoring extracted queries...")
        await ingestor._extract_and_store_sql_queries(test_text, "test_source")
        
        # Check final count
        async with pool.acquire() as conn:
            final_count = await conn.fetchval("SELECT COUNT(*) FROM query_embeddings")
            print(f"Final query_embeddings count: {final_count}")
            
            if final_count > initial_count:
                print(f"SUCCESS: Stored {final_count - initial_count} new SQL queries")
                
                # Show stored queries
                queries = await conn.fetch("""
                    SELECT id, sql_query, query_type, associated_tables
                    FROM query_embeddings 
                    ORDER BY id DESC 
                    LIMIT 5
                """)
                
                print("\nStored queries:")
                for q in queries:
                    print(f"  ID: {q['id']}")
                    print(f"  SQL: {q['sql_query'][:100]}...")
                    print(f"  Type: {q['query_type']}")
                    print(f"  Tables: {q['associated_tables']}")
                    print()
                
                return True
            else:
                print("FAILED: No new SQL queries stored")
                return False
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up test data from database
        try:
            pool = await db.get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM query_embeddings WHERE sql_query LIKE '%sales%' OR sql_query LIKE '%users%' OR sql_query LIKE '%products%'")
                print("Cleaned up test data from query_embeddings table")
        except Exception as e:
            print(f"Warning: error cleaning up test data: {e}")


async def test_sql_metadata_extraction():
    """Test that SQL metadata (tables, columns, joins) is correctly extracted."""
    
    print("\nTesting SQL metadata extraction...")
    
    ingestor = Ingestor()
    
    # Test with a JOIN query
    join_query_text = """
    Example JOIN query:
    SELECT customers.name, orders.total, products.name 
    FROM customers 
    INNER JOIN orders ON customers.id = orders.customer_id
    LEFT JOIN products ON orders.product_id = products.id
    WHERE orders.date > '2024-01-01';
    """
    
    try:
        sql_queries = await ingestor.extract_sql_queries(join_query_text)
        
        if sql_queries:
            query_data = sql_queries[0]
            print(f"Extracted query type: {query_data.get('query_type')}")
            print(f"Tables: {query_data.get('tables')}")
            print(f"Columns: {query_data.get('columns')}")
            print(f"Joins: {json.dumps(query_data.get('joins', []), indent=2)}")
            
            # Verify we extracted join information
            joins = query_data.get('joins', [])
            if len(joins) >= 2:
                print("SUCCESS: Join relationships extracted")
                return True
            else:
                print("WARNING: Join relationships not fully extracted")
                return False
        else:
            print("FAILED: No SQL query extracted from JOIN example")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False


if __name__ == "__main__":
    print("=== SQL Query Extraction Tests ===\n")
    
    # Run direct extraction test
    result1 = asyncio.run(test_sql_extraction_direct())
    
    # Run metadata extraction test  
    result2 = asyncio.run(test_sql_metadata_extraction())
    
    if result1 and result2:
        print("\n=== ALL TESTS PASSED ===")
        sys.exit(0)
    else:
        print("\n=== SOME TESTS FAILED ===")
        sys.exit(1)