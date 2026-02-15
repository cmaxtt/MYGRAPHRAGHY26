// CREATE CONSTRAINTS
CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.patientId IS UNIQUE;
CREATE CONSTRAINT doctor_id IF NOT EXISTS FOR (d:Doctor) REQUIRE d.doctorId IS UNIQUE;
CREATE CONSTRAINT medication_id IF NOT EXISTS FOR (m:Medication) REQUIRE m.medicationId IS UNIQUE;
CREATE CONSTRAINT condition_id IF NOT EXISTS FOR (c:Condition) REQUIRE c.conditionId IS UNIQUE;
CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;

// CREATE DOCTORS
CREATE (d1:Doctor {doctorId:'D1', name:'Dr. Samuel Peters', specialty:'Urology'}) MERGE (e1:Entity {name:'Dr. Samuel Peters'}) SET e1.type = 'Doctor';
CREATE (d2:Doctor {doctorId:'D2', name:'Dr. Karen Mohammed', specialty:'Oncology'}) MERGE (e2:Entity {name:'Dr. Karen Mohammed'}) SET e2.type = 'Doctor';
CREATE (d3:Doctor {doctorId:'D3', name:'Dr. Ian Roberts', specialty:'Endocrinology'}) MERGE (e3:Entity {name:'Dr. Ian Roberts'}) SET e3.type = 'Doctor';
CREATE (d4:Doctor {doctorId:'D4', name:'Dr. Alana Joseph', specialty:'Internal Medicine'}) MERGE (e4:Entity {name:'Dr. Alana Joseph'}) SET e4.type = 'Doctor';
CREATE (d5:Doctor {doctorId:'D5', name:'Dr. Wayne Douglas', specialty:'Nephrology'}) MERGE (e5:Entity {name:'Dr. Wayne Douglas'}) SET e5.type = 'Doctor';
CREATE (d6:Doctor {doctorId:'D6', name:'Dr. Ravi Patel', specialty:'Pulmonology'}) MERGE (e6:Entity {name:'Dr. Ravi Patel'}) SET e6.type = 'Doctor';
CREATE (d7:Doctor {doctorId:'D7', name:'Dr. Natalie King', specialty:'Cardiology'}) MERGE (e7:Entity {name:'Dr. Natalie King'}) SET e7.type = 'Doctor';
CREATE (d8:Doctor {doctorId:'D8', name:'Dr. Colin Fraser', specialty:'Rheumatology'}) MERGE (e8:Entity {name:'Dr. Colin Fraser'}) SET e8.type = 'Doctor';
CREATE (d9:Doctor {doctorId:'D9', name:'Dr. Lisa Wong', specialty:'Psychiatry'}) MERGE (e9:Entity {name:'Dr. Lisa Wong'}) SET e9.type = 'Doctor';
CREATE (d10:Doctor {doctorId:'D10', name:'Dr. Michael Grant', specialty:'Orthopedics'}) MERGE (e10:Entity {name:'Dr. Michael Grant'}) SET e10.type = 'Doctor';

// CREATE MEDICATIONS
CREATE (m1:Medication {medicationId:'M1', name:'Tamsulosin'}) MERGE (e11:Entity {name:'Tamsulosin'}) SET e11.type = 'Medication';
CREATE (m2:Medication {medicationId:'M2', name:'Finasteride'}) MERGE (e12:Entity {name:'Finasteride'}) SET e12.type = 'Medication';
CREATE (m3:Medication {medicationId:'M3', name:'Tamoxifen'}) MERGE (e13:Entity {name:'Tamoxifen'}) SET e13.type = 'Medication';
CREATE (m4:Medication {medicationId:'M4', name:'Ondansetron'}) MERGE (e14:Entity {name:'Ondansetron'}) SET e14.type = 'Medication';
CREATE (m5:Medication {medicationId:'M5', name:'Metformin'}) MERGE (e15:Entity {name:'Metformin'}) SET e15.type = 'Medication';
CREATE (m6:Medication {medicationId:'M6', name:'Insulin Glargine'}) MERGE (e16:Entity {name:'Insulin Glargine'}) SET e16.type = 'Medication';
CREATE (m7:Medication {medicationId:'M7', name:'Amlodipine'}) MERGE (e17:Entity {name:'Amlodipine'}) SET e17.type = 'Medication';
CREATE (m8:Medication {medicationId:'M8', name:'Hydrochlorothiazide'}) MERGE (e18:Entity {name:'Hydrochlorothiazide'}) SET e18.type = 'Medication';
CREATE (m9:Medication {medicationId:'M9', name:'Lisinopril'}) MERGE (e19:Entity {name:'Lisinopril'}) SET e19.type = 'Medication';
CREATE (m10:Medication {medicationId:'M10', name:'Salbutamol'}) MERGE (e20:Entity {name:'Salbutamol'}) SET e20.type = 'Medication';
CREATE (m11:Medication {medicationId:'M11', name:'Budesonide'}) MERGE (e21:Entity {name:'Budesonide'}) SET e21.type = 'Medication';
CREATE (m12:Medication {medicationId:'M12', name:'Aspirin'}) MERGE (e22:Entity {name:'Aspirin'}) SET e22.type = 'Medication';
CREATE (m13:Medication {medicationId:'M13', name:'Atorvastatin'}) MERGE (e23:Entity {name:'Atorvastatin'}) SET e23.type = 'Medication';
CREATE (m14:Medication {medicationId:'M14', name:'Nitroglycerin'}) MERGE (e24:Entity {name:'Nitroglycerin'}) SET e24.type = 'Medication';
CREATE (m15:Medication {medicationId:'M15', name:'Methotrexate'}) MERGE (e25:Entity {name:'Methotrexate'}) SET e25.type = 'Medication';
CREATE (m16:Medication {medicationId:'M16', name:'Folic Acid'}) MERGE (e26:Entity {name:'Folic Acid'}) SET e26.type = 'Medication';
CREATE (m17:Medication {medicationId:'M17', name:'Prednisone'}) MERGE (e27:Entity {name:'Prednisone'}) SET e27.type = 'Medication';
CREATE (m18:Medication {medicationId:'M18', name:'Sertraline'}) MERGE (e28:Entity {name:'Sertraline'}) SET e28.type = 'Medication';
CREATE (m19:Medication {medicationId:'M19', name:'Alprazolam'}) MERGE (e29:Entity {name:'Alprazolam'}) SET e29.type = 'Medication';
CREATE (m20:Medication {medicationId:'M20', name:'Acetaminophen'}) MERGE (e30:Entity {name:'Acetaminophen'}) SET e30.type = 'Medication';

// CREATE CONDITIONS
CREATE (c1:Condition {conditionId:'C1', name:'Benign Prostatic Hyperplasia'}) MERGE (e31:Entity {name:'Benign Prostatic Hyperplasia'}) SET e31.type = 'Condition';
CREATE (c2:Condition {conditionId:'C2', name:'Breast Cancer'}) MERGE (e32:Entity {name:'Breast Cancer'}) SET e32.type = 'Condition';
CREATE (c3:Condition {conditionId:'C3', name:'Type 2 Diabetes'}) MERGE (e33:Entity {name:'Type 2 Diabetes'}) SET e33.type = 'Condition';
CREATE (c4:Condition {conditionId:'C4', name:'Hypertension'}) MERGE (e34:Entity {name:'Hypertension'}) SET e34.type = 'Condition';
CREATE (c5:Condition {conditionId:'C5', name:'Chronic Kidney Disease'}) MERGE (e35:Entity {name:'Chronic Kidney Disease'}) SET e35.type = 'Condition';
CREATE (c6:Condition {conditionId:'C6', name:'Asthma'}) MERGE (e36:Entity {name:'Asthma'}) SET e36.type = 'Condition';
CREATE (c7:Condition {conditionId:'C7', name:'Coronary Artery Disease'}) MERGE (e37:Entity {name:'Coronary Artery Disease'}) SET e37.type = 'Condition';
CREATE (c8:Condition {conditionId:'C8', name:'Rheumatoid Arthritis'}) MERGE (e38:Entity {name:'Rheumatoid Arthritis'}) SET e38.type = 'Condition';
CREATE (c9:Condition {conditionId:'C9', name:'Major Depressive Disorder'}) MERGE (e39:Entity {name:'Major Depressive Disorder'}) SET e39.type = 'Condition';
CREATE (c10:Condition {conditionId:'C10', name:'Osteoarthritis'}) MERGE (e40:Entity {name:'Osteoarthritis'}) SET e40.type = 'Condition';

// EXAMPLE PATIENT CREATE
CREATE (p1:Patient {patientId:'P1', name:'Marcus Allen', diagnosis:'Mild urinary retention', clinical_context:'Marcus Allen presents with mild urinary retention. Assessment suggests Benign Prostatic Hyperplasia (BPH)...'})
MERGE (e41:Entity {name:'Marcus Allen'}) SET e41.type = 'Patient'
WITH p1
MATCH (c1:Condition {conditionId:'C1'})
MATCH (d1:Doctor {doctorId:'D1'})
MATCH (m1:Medication {medicationId:'M1'})
MATCH (m2:Medication {medicationId:'M2'})
MERGE (p1)-[:HAS_CONDITION]->(c1)
MERGE (p1)-[:TREATED_BY]->(d1)
MERGE (p1)-[:PRESCRIBED]->(m1)
MERGE (p1)-[:PRESCRIBED]->(m2);
