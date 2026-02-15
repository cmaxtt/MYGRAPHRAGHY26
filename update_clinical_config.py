import re
with open('ingest_clinical.py', 'r') as f:
    content = f.read()
# Add import config after imports
content = re.sub(r'from db import Database', 'from db import Database\nfrom config import settings', content)
# Replace embed_model assignment
pattern = r'self\.embed_model = "nomic-embed-text"'
replacement = 'self.embed_model = settings.EMBED_MODEL'
new_content = re.sub(pattern, replacement, content)
# Replace data_path assignment
pattern2 = r'self\.data_path = "data/clinical"'
replacement2 = 'self.data_path = settings.DATA_PATH'
new_content = re.sub(pattern2, replacement2, new_content)
with open('ingest_clinical.py', 'w') as f:
    f.write(new_content)
