import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import Database

def verify():
    db = Database()
    
    # Check Neo4j
    driver = db.connect_neo4j()
    with driver.session() as session:
        patient_count = session.run("MATCH (p:Patient) RETURN count(p) as count").single()["count"]
        doctor_count = session.run("MATCH (d:Doctor) RETURN count(d) as count").single()["count"]
        visit_count = session.run("MATCH (v:Visit) RETURN count(v) as count").single()["count"]
        entity_count = session.run("MATCH (e:Entity) RETURN count(e) as count").single()["count"]
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
        print(f"Neo4j: {patient_count} Patients, {doctor_count} Doctors, {visit_count} Visits, {entity_count} Entities, {rel_count} Relationships.")

    # Check Postgres
    conn = db.connect_pg()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM chunks WHERE metadata->>'source' = 'clinical_dataset'")
            vector_count = cur.fetchone()[0]
            print(f"Postgres: {vector_count} clinical chunks embedded.")
    finally:
        db.release_pg(conn)

if __name__ == "__main__":
    verify()
