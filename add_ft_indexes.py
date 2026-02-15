with open('db.py', 'r') as f:
    lines = f.readlines()
new_lines = []
for line in lines:
    new_lines.append(line)
    if 'CREATE FULLTEXT INDEX entity_names_index' in line:
        # Add fulltext indexes for other labels
        indent = line[:line.find('session.run')]
        new_lines.append(indent + 'session.run("CREATE FULLTEXT INDEX patient_names_index IF NOT EXISTS FOR (n:Patient) ON EACH [n.name]")\n')
        new_lines.append(indent + 'session.run("CREATE FULLTEXT INDEX doctor_names_index IF NOT EXISTS FOR (n:Doctor) ON EACH [n.name]")\n')
        new_lines.append(indent + 'session.run("CREATE FULLTEXT INDEX medication_names_index IF NOT EXISTS FOR (n:Medication) ON EACH [n.name]")\n')
        new_lines.append(indent + 'session.run("CREATE FULLTEXT INDEX condition_names_index IF NOT EXISTS FOR (n:Condition) ON EACH [n.name]")\n')
        new_lines.append(indent + 'session.run("CREATE FULLTEXT INDEX visit_ids_index IF NOT EXISTS FOR (n:Visit) ON EACH [n.visitId]")\n')
with open('db.py', 'w') as f:
    f.writelines(new_lines)
