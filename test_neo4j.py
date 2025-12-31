from neo4j import GraphDatabase
import os

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PWD = "password"

def test_conn():
    print("Testing Neo4j connection...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
        driver.verify_connectivity()
        print("Success!")
        driver.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_conn()
