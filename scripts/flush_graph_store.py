"""
Flush/clear all data from Neo4j graph database.
"""
import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import Database

async def flush_graph_store():
    """Delete all nodes and relationships from Neo4j."""
    db = Database()
    try:
        driver = await db.get_neo4j_driver()
        async with driver.session() as session:
            # First, check current node count
            result = await session.run("MATCH (n) RETURN COUNT(n) AS count")
            record = await result.single()
            node_count = record["count"]
            print(f"Current Neo4j node count: {node_count}")
            
            if node_count > 0:
                # Delete all nodes and relationships
                # Note: Must delete relationships first in Neo4j
                deleted = await session.run("MATCH (n) DETACH DELETE n")
                print(f"Deleted {node_count} nodes and all relationships")
                
                # Verify deletion
                result = await session.run("MATCH (n) RETURN COUNT(n) AS count")
                record = await result.single()
                final_count = record["count"]
                print(f"Verified: Neo4j now has {final_count} nodes")
            else:
                print("Neo4j is already empty")
                
    except Exception as e:
        print(f"Error flushing graph store: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

def main():
    print("Flushing Neo4j graph store...")
    asyncio.run(flush_graph_store())
    print("Graph flush completed.")

if __name__ == "__main__":
    main()