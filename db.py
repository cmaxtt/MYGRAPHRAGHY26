import os
import psycopg2
from psycopg2 import pool
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
from config import settings

# PostgreSQL configuration
PG_HOST = settings.PG_HOST
PG_PORT = settings.PG_PORT
PG_USER = settings.PG_USER
PG_PWD = settings.PG_PWD
PG_DB = settings.PG_DB

# Neo4j configuration
NEO4J_URI = settings.NEO4J_URI
NEO4J_USER = settings.NEO4J_USER
NEO4J_PWD = settings.NEO4J_PWD

class Database:
    _pg_pool = None

    def __init__(self):
        self.neo4j_driver = None
        self._init_pg_pool()

    def _init_pg_pool(self):
        if Database._pg_pool is None:
            try:
                Database._pg_pool = pool.SimpleConnectionPool(
                    1, 10,
                    host=PG_HOST,
                    port=PG_PORT,
                    user=PG_USER,
                    password=PG_PWD,
                    dbname=PG_DB
                )
                print("PostgreSQL connection pool initialized")
            except Exception as e:
                print(f"Error initializing PG pool: {e}")

    def connect_pg(self):
        if Database._pg_pool:
            return Database._pg_pool.getconn()
        return None

    def release_pg(self, conn):
        if Database._pg_pool and conn:
            Database._pg_pool.putconn(conn)

    def connect_neo4j(self):
        retries = 5
        while retries > 0:
            try:
                if self.neo4j_driver is None:
                    self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
                    self.neo4j_driver.verify_connectivity()
                    logger.info("Connected to Neo4j")
                return self.neo4j_driver
            except Exception as e:
                logger.error(f"Error connecting to Neo4j: {e}. Retrying...")
                time.sleep(2)
                retries -= 1
        raise Exception("Failed to connect to Neo4j")

    def init_db(self):
        # Initialize PostgreSQL
        conn = self.connect_pg()
        if conn:
            try:
                conn.autocommit = True
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
                    cur.execute("CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops)")
            finally:
                self.release_pg(conn)
        
        # Initialize Neo4j constraints
        driver = self.connect_neo4j()
        with driver.session() as session:
            # General Entity constraints (from original)
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
            session.run("CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            session.run("CREATE FULLTEXT INDEX entity_names_index IF NOT EXISTS FOR (n:Entity) ON EACH [n.name]")
            session.run("CREATE FULLTEXT INDEX patient_names_index IF NOT EXISTS FOR (n:Patient) ON EACH [n.name]")
            session.run("CREATE FULLTEXT INDEX doctor_names_index IF NOT EXISTS FOR (n:Doctor) ON EACH [n.name]")
            session.run("CREATE FULLTEXT INDEX medication_names_index IF NOT EXISTS FOR (n:Medication) ON EACH [n.name]")
            session.run("CREATE FULLTEXT INDEX condition_names_index IF NOT EXISTS FOR (n:Condition) ON EACH [n.name]")
            session.run("CREATE FULLTEXT INDEX visit_ids_index IF NOT EXISTS FOR (n:Visit) ON EACH [n.visitId]")
            
            # Clinical Specific constraints
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Patient) REQUIRE p.patientId IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Doctor) REQUIRE d.doctorId IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Medication) REQUIRE m.medicationId IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Condition) REQUIRE c.conditionId IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (v:Visit) REQUIRE v.visitId IS UNIQUE")

    def close(self):
        if Database._pg_pool:
            Database._pg_pool.closeall()
        if self.neo4j_driver:
            self.neo4j_driver.close()

if __name__ == "__main__":
    db = Database()
    db.init_db()
    db.close()
# Test comment
