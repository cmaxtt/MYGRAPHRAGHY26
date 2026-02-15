import os
import pandas as pd
import ollama
import json
from db import Database
from typing import List
import time

class ClinicalIngestor:
    def __init__(self):
        self.db = Database()
        self.embed_model = "nomic-embed-text"
        self.data_path = "data/clinical"

    def get_embedding(self, text: str) -> List[float]:
        try:
            response = ollama.embeddings(model=self.embed_model, prompt=text)
            return response['embedding']
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return [0.0] * 768

    def ingest_nodes(self):
        # Load CSVs
        doctors = pd.read_csv(os.path.join(self.data_path, "doctors.csv"))
        medications = pd.read_csv(os.path.join(self.data_path, "medications.csv"))
        conditions = pd.read_csv(os.path.join(self.data_path, "conditions.csv"))
        patients = pd.read_csv(os.path.join(self.data_path, "patients.csv"))
        visits = pd.read_csv(os.path.join(self.data_path, "visits.csv"))

        driver = self.db.connect_neo4j()
        with driver.session() as session:
            print("Ingesting Doctors...")
            for _, row in doctors.iterrows():
                session.run("""
                    MERGE (d:Doctor {doctorId: $id})
                    SET d.name = $name, d.specialty = $specialty
                    MERGE (e:Entity {name: $name})
                    SET e.type = 'Doctor'
                """, id=row['doctorId'], name=row['name'], specialty=row['specialty'])

            print("Ingesting Medications...")
            for _, row in medications.iterrows():
                session.run("""
                    MERGE (m:Medication {medicationId: $id})
                    SET m.name = $name
                    MERGE (e:Entity {name: $name})
                    SET e.type = 'Medication'
                """, id=row['medicationId'], name=row['name'])

            print("Ingesting Conditions...")
            for _, row in conditions.iterrows():
                session.run("""
                    MERGE (c:Condition {conditionId: $id})
                    SET c.name = $name
                    MERGE (e:Entity {name: $name})
                    SET e.type = 'Condition'
                """, id=row['conditionId'], name=row['name'])

            print("Ingesting Visits...")
            for _, row in visits.iterrows():
                session.run("""
                    MERGE (v:Visit {visitId: $id})
                    SET v.date = $date
                """, id=row['visitId'], date=row['date'])

            print(f"Ingesting {len(patients)} Patients and generating Vector embeddings...")
            conn = self.db.connect_pg()
            try:
                conn.autocommit = True
                with conn.cursor() as cur:
                    for i, row in patients.iterrows():
                        if i % 50 == 0:
                            print(f"  Processed {i}/{len(patients)} patients...")
                        
                        # Neo4j
                        session.run("""
                            MERGE (p:Patient {patientId: $id})
                            SET p.name = $name, p.address = $address, p.city = $city, 
                                p.phone = $phone, p.diagnosis = $diagnosis, p.clinical_context = $context
                            MERGE (e:Entity {name: $name})
                            SET e.type = 'Patient'
                        """, id=row['patientId'], name=row['name'], address=row['address'], 
                           city=row['city'], phone=row['phone'], diagnosis=row['diagnosis'], 
                           context=row['clinical_context'])

                        # Postgres (Vector)
                        embedding = self.get_embedding(row['clinical_context'])
                        cur.execute(
                            "INSERT INTO chunks (content, metadata, embedding) VALUES (%s, %s, %s)",
                            (row['clinical_context'], json.dumps({"source": "clinical_dataset", "patientId": row['patientId']}), embedding)
                        )
            finally:
                self.db.release_pg(conn)

    def ingest_relationships(self):
        rel_df = pd.read_csv(os.path.join(self.data_path, "relationships.csv"))
        driver = self.db.connect_neo4j()
        print(f"Ingesting {len(rel_df)} Relationships...")
        
        # Batching relationships for performance
        batch_size = 500
        with driver.session() as session:
            for i in range(0, len(rel_df), batch_size):
                batch = rel_df.iloc[i:i+batch_size]
                if i % 1000 == 0:
                    print(f"  Ingested {i}/{len(rel_df)} relationships...")
                
                for _, row in batch.iterrows():
                    # Optimized MATCH using IDs and Labels
                    query = f"""
                    MATCH (s) WHERE (s:Patient OR s:Visit OR s:Doctor OR s:Medication OR s:Condition) AND 
                            (s.patientId = $startId OR s.visitId = $startId OR s.doctorId = $startId OR s.medicationId = $startId OR s.conditionId = $startId)
                    MATCH (e) WHERE (e:Patient OR e:Visit OR e:Doctor OR e:Medication OR e:Condition) AND 
                            (e.patientId = $endId OR e.visitId = $endId OR e.doctorId = $endId OR e.medicationId = $endId OR e.conditionId = $endId)
                    MERGE (s)-[r:{row['relationship']}]->(e)
                    """
                    session.run(query, startId=row['startId'], endId=row['endId'])

    def run(self):
        start_time = time.time()
        self.ingest_nodes()
        self.ingest_relationships()
        duration = time.time() - start_time
        print(f"Ingestion complete in {duration:.2f} seconds.")

if __name__ == "__main__":
    ingestor = ClinicalIngestor()
    ingestor.run()
