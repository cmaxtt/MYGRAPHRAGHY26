"""
Clinical data ingestor for processing CSV files with patient, doctor, medication, etc. data.
"""
import os
import json
import logging
import pandas as pd
import time
from typing import List

from base_ingestor import BaseIngestor
from config import settings


logger = logging.getLogger(__name__)


class ClinicalIngestor(BaseIngestor):
    """Clinical data ingestor for CSV datasets."""
    
    def __init__(self, db=None):
        """
        Initialize clinical ingestor.
        
        Args:
            db: Database instance (optional)
        """
        super().__init__(db)
        self.data_path = settings.DATA_PATH
    
    def ingest_nodes(self) -> None:
        """Ingest all clinical nodes from CSV files."""
        # Load CSVs
        doctors = pd.read_csv(os.path.join(self.data_path, "doctors.csv"))
        medications = pd.read_csv(os.path.join(self.data_path, "medications.csv"))
        conditions = pd.read_csv(os.path.join(self.data_path, "conditions.csv"))
        patients = pd.read_csv(os.path.join(self.data_path, "patients.csv"))
        visits = pd.read_csv(os.path.join(self.data_path, "visits.csv"))
        
        driver = self.db.connect_neo4j()
        with driver.session() as session:
            logger.info("Ingesting Doctors...")
            for _, row in doctors.iterrows():
                session.run("""
                    MERGE (d:Doctor {doctorId: $id})
                    SET d.name = $name, d.specialty = $specialty
                    SET d:Entity
                """, id=row['doctorId'], name=row['name'], specialty=row['specialty'])
            
            logger.info("Ingesting Medications...")
            for _, row in medications.iterrows():
                session.run("""
                    MERGE (m:Medication {medicationId: $id})
                    SET m.name = $name
                    SET m:Entity
                """, id=row['medicationId'], name=row['name'])
            
            logger.info("Ingesting Conditions...")
            for _, row in conditions.iterrows():
                session.run("""
                    MERGE (c:Condition {conditionId: $id})
                    SET c.name = $name
                    SET c:Entity
                """, id=row['conditionId'], name=row['name'])
            
            logger.info("Ingesting Visits...")
            for _, row in visits.iterrows():
                session.run("""
                    MERGE (v:Visit {visitId: $id})
                    SET v.date = $date
                    SET v:Entity
                    SET v.name = 'Visit ' + $id
                """, id=row['visitId'], date=row['date'])
            
            logger.info(f"Ingesting {len(patients)} Patients and generating Vector embeddings...")
            conn = self.db.connect_pg()
            try:
                conn.autocommit = True
                with conn.cursor() as cur:
                    for i, row in patients.iterrows():
                        if i % 50 == 0:
                            logger.info(f"  Processed {i}/{len(patients)} patients...")
                        
                        # Neo4j
                        session.run("""
                            MERGE (p:Patient {patientId: $id})
                            SET p.name = $name, p.address = $address, p.city = $city, 
                                p.phone = $phone, p.diagnosis = $diagnosis, p.clinical_context = $context
                            SET p:Entity
                        """, id=row['patientId'], name=row['name'], address=row['address'], 
                           city=row['city'], phone=row['phone'], diagnosis=row['diagnosis'], 
                           context=row['clinical_context'])
                        
                        # Postgres (Vector) - use batch cursor
                        embedding = self.get_embedding(row['clinical_context'])
                        self._store_vector_with_cursor(
                            cur,
                            row['clinical_context'],
                            embedding,
                            {"source": "clinical_dataset", "patientId": row['patientId']}
                        )
            finally:
                self.db.release_pg(conn)
    
    def ingest_relationships(self) -> None:
        """Ingest relationships between clinical entities."""
        rel_df = pd.read_csv(os.path.join(self.data_path, "relationships.csv"))
        driver = self.db.connect_neo4j()
        logger.info(f"Ingesting {len(rel_df)} Relationships...")
        
        # Batching relationships for performance
        batch_size = 500
        with driver.session() as session:
            for i in range(0, len(rel_df), batch_size):
                batch = rel_df.iloc[i:i+batch_size]
                if i % 1000 == 0:
                    logger.info(f"  Ingested {i}/{len(rel_df)} relationships...")
                
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
    
    def run(self) -> None:
        """Run full ingestion pipeline."""
        start_time = time.time()
        self.ingest_nodes()
        self.ingest_relationships()
        duration = time.time() - start_time
        logger.info(f"Ingestion complete in {duration:.2f} seconds.")


if __name__ == "__main__":
    ingestor = ClinicalIngestor()
    ingestor.run()