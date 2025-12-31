import os
import psycopg2
from neo4j import GraphDatabase
from dotenv import load_dotenv
import time

load_dotenv()

# PostgreSQL configuration
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PWD = os.getenv("PG_PWD", "password")
PG_DB = os.getenv("PG_DB", "graphrag")

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PWD = os.getenv("NEO4J_PWD", "password")

class Database:
    def __init__(self):
        self.pg_conn = None
        self.neo4j_driver = None

    def connect_pg(self):
        retries = 5
        while retries > 0:
            try:
                self.pg_conn = psycopg2.connect(
                    host=PG_HOST,
                    port=PG_PORT,
                    user=PG_USER,
                    password=PG_PWD,
                    dbname=PG_DB
                )
                self.pg_conn.autocommit = True
                print("Connected to PostgreSQL")
                return self.pg_conn
            except Exception as e:
                print(f"Error connecting to PostgreSQL: {e}. Retrying...")
                time.sleep(2)
                retries -= 1
        raise Exception("Failed to connect to PostgreSQL")

    def connect_neo4j(self):
        retries = 5
        while retries > 0:
            try:
                self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
                self.neo4j_driver.verify_connectivity()
                print("Connected to Neo4j")
                return self.neo4j_driver
            except Exception as e:
                print(f"Error connecting to Neo4j: {e}. Retrying...")
                time.sleep(2)
                retries -= 1
        raise Exception("Failed to connect to Neo4j")

    def init_db(self):
        # Initialize PostgreSQL
        conn = self.connect_pg()
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id SERIAL PRIMARY KEY,
                    content TEXT,
                    metadata JSONB,
                    embedding vector(768)
                );
            """)
        
        # Initialize Neo4j constraints
        driver = self.connect_neo4j()
        with driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
            session.run("CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type)")

    def close(self):
        if self.pg_conn:
            self.pg_conn.close()
        if self.neo4j_driver:
            self.neo4j_driver.close()

if __name__ == "__main__":
    db = Database()
    db.init_db()
    db.close()
