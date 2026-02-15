import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import Database

def clear_databases():
    db = Database()
    
    # 1. Clear Neo4j
    print("Clearing Neo4j data...")
    try:
        driver = db.connect_neo4j()
        with driver.session() as session:
            # Delete all nodes and relationships
            result = session.run("MATCH (n) DETACH DELETE n")
            summary = result.consume()
            print(f"  Neo4j cleanup: Deleted {summary.counters.nodes_deleted} nodes and {summary.counters.relationships_deleted} relationships.")
    except Exception as e:
        print(f"Error clearing Neo4j: {e}")

    # 2. Clear PostgreSQL
    print("Clearing PostgreSQL data...")
    conn = db.connect_pg()
    if conn:
        try:
            conn.autocommit = True
            with conn.cursor() as cur:
                # Truncate the chunks table
                cur.execute("TRUNCATE TABLE chunks RESTART IDENTITY;")
                print("  PostgreSQL cleanup: Table 'chunks' truncated and identity reset.")
        except Exception as e:
            print(f"Error clearing PostgreSQL: {e}")
        finally:
            db.release_pg(conn)
    else:
        print("Could not connect to PostgreSQL.")

    db.close()
    print("Database cleanup complete.")

if __name__ == "__main__":
    clear_databases()
