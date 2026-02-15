import random
import datetime
import os

# Set seed for reproducibility
random.seed(42)

# Configuration
DATA_DIR = "data/clinical"
os.makedirs(DATA_DIR, exist_ok=True)

first_names = ['Marcus', 'Alicia', 'Jonathan', 'Renata', 'Keith', 'Sonia', 'Devon', 'Leila', 'Raj', 'Maria', 'Ian', 'Alana', 'Wayne', 'Ravi', 'Natalie', 'Colin', 'Lisa', 'Michael', 'Emily', 'James', 'Sarah', 'David', 'Anna', 'Robert', 'Linda', 'John', 'Patricia', 'Thomas', 'Barbara', 'Christopher']
last_names = ['Allen', 'Gomez', 'Pierre', 'Singh', 'Douglas', 'Joseph', 'Patel', 'King', 'Fraser', 'Wong', 'Grant', 'Carter', 'Lee', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson', 'White', 'Harris']
streets = ['Cedar Lane', 'Palm View Drive', 'Valley Road', 'Orchid Crescent', 'Bamboo Grove', 'Mango Street', 'Coconut Avenue', 'Pine Hill', 'Rose Garden', 'Lily Path', 'Oak Street', 'Elm Road', 'Maple Avenue', 'Birch Lane', 'Willow Drive', 'Spruce Court', 'Fir Terrace', 'Cedar Boulevard', 'Palm Boulevard', 'Valley Boulevard']
cities = ['Port of Spain', 'San Fernando', 'Chaguanas', 'Tunapuna', 'Arima', 'Point Fortin', 'Scarborough', 'Diego Martin', 'Couva', 'Princes Town', 'Siparia', 'Penal', 'Sangre Grande', 'Tobago', 'Mayaro']

diagnoses_dict = {
    'C1': ['Mild urinary retention', 'Enlarged prostate with lower urinary tract symptoms', 'BPH with nocturia', 'Prostatic hyperplasia causing urinary hesitation'],
    'C2': ['Stage II invasive ductal carcinoma', 'Early-stage breast cancer', 'Hormone-positive breast cancer', 'Breast cancer with lymph node involvement'],
    'C3': ['Poor glycemic control', 'Type 2 diabetes with high HbA1c', 'Diabetic with peripheral neuropathy', 'Hyperglycemia in type 2 diabetes'],
    'C4': ['Stage 1 hypertension', 'Essential hypertension', 'High blood pressure without organ damage', 'Borderline hypertension'],
    'C5': ['Stage 3 chronic kidney disease', 'CKD with decreased GFR', 'Kidney disease due to diabetes', 'Proteinuria in CKD'],
    'C6': ['Mild persistent asthma', 'Asthma with frequent wheezing', 'Allergic asthma triggered by pollen', 'Asthma exacerbation due to infection'],
    'C7': ['Stable coronary artery disease', 'CAD with angina', 'Post-stent placement follow-up', 'Atherosclerosis of coronary arteries'],
    'C8': ['Active rheumatoid arthritis', 'RA with joint swelling', 'Seropositive rheumatoid arthritis', 'RA causing fatigue and stiffness'],
    'C9': ['Major depressive disorder', 'Depression with anhedonia', 'Recurrent depressive episodes', 'Depression with sleep disturbance'],
    'C10': ['Osteoarthritis of the knee', 'Degenerative arthritis in hip', 'OA with joint pain', 'Spinal osteoarthritis causing back pain']
}

doctors_dict = {
    'D1': {'name': 'Dr. Samuel Peters', 'specialty': 'Urology'},
    'D2': {'name': 'Dr. Karen Mohammed', 'specialty': 'Oncology'},
    'D3': {'name': 'Dr. Ian Roberts', 'specialty': 'Endocrinology'},
    'D4': {'name': 'Dr. Alana Joseph', 'specialty': 'Internal Medicine'},
    'D5': {'name': 'Dr. Wayne Douglas', 'specialty': 'Nephrology'},
    'D6': {'name': 'Dr. Ravi Patel', 'specialty': 'Pulmonology'},
    'D7': {'name': 'Dr. Natalie King', 'specialty': 'Cardiology'},
    'D8': {'name': 'Dr. Colin Fraser', 'specialty': 'Rheumatology'},
    'D9': {'name': 'Dr. Lisa Wong', 'specialty': 'Psychiatry'},
    'D10': {'name': 'Dr. Michael Grant', 'specialty': 'Orthopedics'},
    'D11': {'name': 'Dr. Emily Carter', 'specialty': 'Neurology'},
    'D12': {'name': 'Dr. James Lee', 'specialty': 'Gastroenterology'}
}

meds_dict = {
    'M1': 'Tamsulosin', 'M2': 'Finasteride', 'M3': 'Tamoxifen', 'M4': 'Ondansetron', 'M5': 'Metformin',
    'M6': 'Insulin Glargine', 'M7': 'Amlodipine', 'M8': 'Hydrochlorothiazide', 'M9': 'Lisinopril', 'M10': 'Salbutamol',
    'M11': 'Budesonide', 'M12': 'Aspirin', 'M13': 'Atorvastatin', 'M14': 'Nitroglycerin', 'M15': 'Methotrexate',
    'M16': 'Folic Acid', 'M17': 'Prednisone', 'M18': 'Sertraline', 'M19': 'Alprazolam', 'M20': 'Acetaminophen',
    'M21': 'Ibuprofen', 'M22': 'Omeprazole', 'M23': 'Levothyroxine', 'M24': 'Metoprolol', 'M25': 'Warfarin'
}

conditions_dict = {
    'C1': 'Benign Prostatic Hyperplasia', 'C2': 'Breast Cancer', 'C3': 'Type 2 Diabetes', 'C4': 'Hypertension',
    'C5': 'Chronic Kidney Disease', 'C6': 'Asthma', 'C7': 'Coronary Artery Disease', 'C8': 'Rheumatoid Arthritis',
    'C9': 'Major Depressive Disorder', 'C10': 'Osteoarthritis'
}

patients_list = []
visits_list = []
relationships_list = []
visit_counter = 1

for pid in range(1, 501):
    p_id = f'P{pid}'
    fname = random.choice(first_names)
    lname = random.choice(last_names)
    name = f'{fname} {lname}'
    addr_num = random.randint(1, 200)
    street = random.choice(streets)
    address = f'{addr_num} {street}'
    city = random.choice(cities)
    phone = f'868-555-{random.randint(1000, 9999):04d}'
    cond_id = f'C{random.randint(1, 10)}'
    diagnosis = random.choice(diagnoses_dict[cond_id])
    
    # Generate a narrative clinical context for vector RAG
    context = f"Patient {name} ({p_id}), residing at {address}, {city}. "
    context += f"Diagnosed with {conditions_dict[cond_id]} specifically presenting as {diagnosis}. "
    context += f"Contact: {phone}. History shows regular checkups and medication compliance."
    
    patients_list.append(f'{p_id},"{name}","{address}","{city}","{phone}","{diagnosis}","{context}"')
    relationships_list.append(f'{p_id},HAS_CONDITION,{cond_id}')
    
    num_visits = random.randint(2, 5)
    date_list = [datetime.date(2025, 1, 1) + datetime.timedelta(days=random.randint(0, 358)) for _ in range(num_visits)]
    date_list.sort()
    
    for v_date in date_list:
        v_id = f'V{visit_counter}'
        visit_counter += 1
        visits_list.append(f'{v_id},{v_date.strftime("%Y-%m-%d")}')
        relationships_list.append(f'{p_id},HAS_VISIT,{v_id}')
        doc_id = f'D{random.randint(1, 12)}'
        relationships_list.append(f'{v_id},TREATED_BY,{doc_id}')
        
        num_meds = random.randint(1, 3)
        selected_meds = random.sample(list(meds_dict.keys()), k=num_meds)
        for m_id in selected_meds:
            relationships_list.append(f'{v_id},PRESCRIBED,{m_id}')

# Save CSVs
print(f"Generating CSVs in {DATA_DIR}...")
with open(os.path.join(DATA_DIR, 'patients.csv'), 'w', encoding='utf-8') as f:
    f.write('patientId,name,address,city,phone,diagnosis,clinical_context\n' + '\n'.join(patients_list))
with open(os.path.join(DATA_DIR, 'doctors.csv'), 'w', encoding='utf-8') as f:
    f.write('doctorId,name,specialty\n' + '\n'.join(f'{k},"{v["name"]}","{v["specialty"]}"' for k, v in doctors_dict.items()))
with open(os.path.join(DATA_DIR, 'medications.csv'), 'w', encoding='utf-8') as f:
    f.write('medicationId,name\n' + '\n'.join(f'{k},"{v}"' for k, v in meds_dict.items()))
with open(os.path.join(DATA_DIR, 'conditions.csv'), 'w', encoding='utf-8') as f:
    f.write('conditionId,name\n' + '\n'.join(f'{k},"{v}"' for k, v in conditions_dict.items()))
with open(os.path.join(DATA_DIR, 'visits.csv'), 'w', encoding='utf-8') as f:
    f.write('visitId,date\n' + '\n'.join(visits_list))
with open(os.path.join(DATA_DIR, 'relationships.csv'), 'w', encoding='utf-8') as f:
    f.write('startId,relationship,endId\n' + '\n'.join(relationships_list))

print('CSVs generated successfully.')
