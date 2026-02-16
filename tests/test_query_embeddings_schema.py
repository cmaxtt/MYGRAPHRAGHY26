#!/usr/bin/env python3
"""Test query_embeddings schema and CRUD operations."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import Database


async def test_schema():
    """Test that query_embeddings table exists and has correct columns."""
    db = Database()
    pool = await db.get_pg_pool()
    
    async with pool.acquire() as conn:
        # Check table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'query_embeddings'
            );
        """)
        print(f"Table query_embeddings exists: {table_exists}")
        
        if not table_exists:
            print("ERROR: query_embeddings table not found!")
            return False
        
        # Check columns
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'query_embeddings'
            ORDER BY ordinal_position;
        """)
        
        print("\nColumns in query_embeddings:")
        for col in columns:
            print(f"  {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Check indexes
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'query_embeddings'
            ORDER BY indexname;
        """)
        
        print("\nIndexes on query_embeddings:")
        for idx in indexes:
            print(f"  {idx['indexname']}")
        
        # Test inserting a sample query
        from api_client import api_client
        embeddings = await api_client.get_embeddings(["Sample SQL query for testing"])
        embedding = embeddings[0]  # Get first embedding
        
        query_id = await db.insert_query_embedding(
            question="What are the total sales per customer?",
            sql_query="SELECT customer_id, SUM(amount) FROM sales GROUP BY customer_id;",
            embedding=embedding,
            query_type="SELECT",
            associated_tables=["sales", "customers"],
            table_links={"joins": [{"from": "sales", "to": "customers", "on": "sales.customer_id = customers.id"}]},
            used_columns=["customer_id", "amount"],
            database_schema="public"
        )
        print(f"\nInserted query with ID: {query_id}")
        
        # Test retrieval
        query = await db.get_query_by_id(query_id)
        print(f"Retrieved query: {query['question']}")
        print(f"SQL: {query['sql_query']}")
        
        # Test search
        results = await db.search_query_embeddings(embedding, limit=3)
        print(f"\nSearch returned {len(results)} results:")
        for r in results:
            print(f"  - {r['question']} (similarity: {r['similarity']:.4f})")
        
        # Test deactivation
        await db.deactivate_query(query_id)
        query_after = await db.get_query_by_id(query_id)
        print(f"\nQuery active after deactivation: {query_after['is_active']}")
        
        # Clean up test data
        async with pool.acquire() as conn2:
            await conn2.execute("DELETE FROM query_embeddings WHERE id = $1", query_id)
        
        return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_schema())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)