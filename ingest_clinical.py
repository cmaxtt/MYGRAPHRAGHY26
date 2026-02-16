"""
Clinical data ingestor for processing CSV files with patient, doctor, medication, etc. data.
"""
import os
import json
import logging
import pandas as pd
import time
import asyncio
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
    
    async def ingest_nodes(self) -> None:
        """Ingest all clinical nodes from CSV files."""
        # Load CSVs
        # Ensure data path exists
        if not os.path.exists(self.data_path):
            logger.error(f"Data path {self.data_path} does not exist.")
            return

        doctors = pd.read_csv(os.path.join(self.data_path, "doctors.csv"))
        medications = pd.read_csv(os.path.join(self.data_path, "medications.csv"))
        conditions = pd.read_csv(os.path.join(self.data_path, "conditions.csv"))
        patients = pd.read_csv(os.path.join(self.data_path, "patients.csv"))
        visits = pd.read_csv(os.path.join(self.data_path, "visits.csv"))
        
        driver = await self.db.get_neo4j_driver()
        async with driver.session() as session:
            logger.info("Ingesting Doctors...")
            for _, row in doctors.iterrows():
                await session.run("""
                    MERGE (d:Doctor {doctorId: $id})
                    SET d.name = $name, d.specialty = $specialty
                    SET d:Entity
                """, id=str(row['doctorId']), name=row['name'], specialty=row['specialty'])
            
            logger.info("Ingesting Medications...")
            for _, row in medications.iterrows():
                await session.run("""
                    MERGE (m:Medication {medicationId: $id})
                    SET m.name = $name
                    SET m:Entity
                """, id=str(row['medicationId']), name=row['name'])
            
            logger.info("Ingesting Conditions...")
            for _, row in conditions.iterrows():
                await session.run("""
                    MERGE (c:Condition {conditionId: $id})
                    SET c.name = $name
                    SET c:Entity
                """, id=str(row['conditionId']), name=row['name'])
            
            logger.info("Ingesting Visits...")
            for _, row in visits.iterrows():
                await session.run("""
                    MERGE (v:Visit {visitId: $id})
                    SET v.date = $date
                    SET v:Entity
                    SET v.name = 'Visit ' + $id
                """, id=str(row['visitId']), date=row['date'])
            
            logger.info(f"Ingesting {len(patients)} Patients and generating Vector embeddings...")
            
            # Prepare patient data for batch embedding
            patient_texts = []
            patient_metadatas = []
            
            for _, row in patients.iterrows():
                # Neo4j ingestion (can be per row or batched, per row is fine for small datasets)
                await session.run("""
                    MERGE (p:Patient {patientId: $id})
                    SET p.name = $name, p.address = $address, p.city = $city, 
                        p.phone = $phone, p.diagnosis = $diagnosis, p.clinical_context = $context
                    SET p:Entity
                """, id=str(row['patientId']), name=row['name'], address=row['address'], 
                   city=row['city'], phone=row['phone'], diagnosis=row['diagnosis'], 
                   context=row['clinical_context'])
                
                patient_texts.append(row['clinical_context'])
                patient_metadatas.append({"source": "clinical_dataset", "patientId": str(row['patientId'])})

            # Batch Embedding Ingestion
            batch_size = settings.BATCH_SIZE_EMBEDDINGS
            pool = await self.db.get_pg_pool()
            
            async with pool.acquire() as conn:
                for i in range(0, len(patient_texts), batch_size):
                    batch_texts = patient_texts[i:i+batch_size]
                    batch_metadatas = patient_metadatas[i:i+batch_size]
                    
                    logger.info(f"  Embedding batch {i//batch_size + 1}/{(len(patient_texts)-1)//batch_size + 1}...")
                    
                    try:
                        embeddings = await self.api_client.get_embeddings(batch_texts)
                        
                        # Store in Postgres
                        for j, text in enumerate(batch_texts):
                            await self._store_vector_with_conn(
                                conn,
                                text,
                                embeddings[j],
                                batch_metadatas[j]
                            )
                    except Exception as e:
                        logger.error(f"Error processing batch {i}: {e}")

    
    async def ingest_relationships(self) -> None:
        """Ingest relationships between clinical entities."""
        if not os.path.exists(self.data_path):
            return

        rel_df = pd.read_csv(os.path.join(self.data_path, "relationships.csv"))
        driver = await self.db.get_neo4j_driver()
        logger.info(f"Ingesting {len(rel_df)} Relationships...")
        
        # Batching relationships for performance
        batch_size = 500
        async with driver.session() as session:
            for i in range(0, len(rel_df), batch_size):
                batch = rel_df.iloc[i:i+batch_size]
                if i % 1000 == 0:
                    logger.info(f"  Ingested {i}/{len(rel_df)} relationships...")
                
                for _, row in batch.iterrows():
                    # Optimized MATCH using IDs and Labels
                    # Note: We cast IDs to string to match node ingestion
                    query = f"""
                    MATCH (s) WHERE (s:Patient OR s:Visit OR s:Doctor OR s:Medication OR s:Condition) AND 
                            (s.patientId = $startId OR s.visitId = $startId OR s.doctorId = $startId OR s.medicationId = $startId OR s.conditionId = $startId)
                    MATCH (e) WHERE (e:Patient OR e:Visit OR e:Doctor OR e:Medication OR e:Condition) AND 
                            (e.patientId = $endId OR e.visitId = $endId OR e.doctorId = $endId OR e.medicationId = $endId OR e.conditionId = $endId)
                    MERGE (s)-[r:{row['relationship']}]->(e)
                    """
                    await session.run(query, startId=str(row['startId']), endId=str(row['endId']))
    
    async def run(self) -> None:
        """Run full ingestion pipeline."""
        start_time = time.time()
        await self.db.init_db() # Ensure DB is initialized
        await self.ingest_nodes()
        await self.ingest_relationships()
        duration = time.time() - start_time
        logger.info(f"Ingestion complete in {duration:.2f} seconds.")


if __name__ == "__main__":
    async def main():
        ingestor = ClinicalIngestor()
        await ingestor.run()
        await ingestor.close()
    
    asyncio.run(main())