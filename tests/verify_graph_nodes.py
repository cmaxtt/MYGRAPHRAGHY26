from neo4j import GraphDatabase
import os
import sys

# Add parent dir to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

def verify_graph():
    uri = settings.NEO4J_URI
    user = settings.NEO4J_USER
    pwd = settings.NEO4J_PWD
    
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    
    print("\nVerifying Graph Node Labels...")
    try:
        with driver.session() as session:
            # Check Doctor nodes
            result = session.run("MATCH (n:Doctor) RETURN count(n) as count, sum(CASE WHEN n:Entity THEN 1 ELSE 0 END) as entity_count")
            record = result.single()
            doc_count = record['count']
            doc_entity_count = record['entity_count']
            
            print(f"Doctor Nodes: {doc_count}")
            print(f"Doctor Nodes with 'Entity' label: {doc_entity_count}")
            
            if doc_count > 0 and doc_count == doc_entity_count:
                print("SUCCESS: All Doctor nodes have the unified 'Entity' label.")
            else:
                print("FAILURE: Mismatch in labels.")
            
            # Check Visits
            result = session.run("MATCH (n:Visit) RETURN count(n) as count, sum(CASE WHEN n:Entity THEN 1 ELSE 0 END) as entity_count")
            record = result.single()
            visit_count = record['count']
            print(f"Visit Nodes: {visit_count}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    verify_graph()
