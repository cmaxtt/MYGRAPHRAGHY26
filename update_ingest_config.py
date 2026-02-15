import re
with open('ingest.py', 'r') as f:
    content = f.read()
# Add import config after imports
content = re.sub(r'from db import Database', 'from db import Database\nfrom config import settings', content)
# Replace embed_model and llm_model assignments
pattern = r'self\.embed_model = "nomic-embed-text"\s*\n\s*self\.llm_model = "gpt-oss:20b-cloud"'
replacement = 'self.embed_model = settings.EMBED_MODEL\n        self.llm_model = settings.LLM_MODEL'
new_content = re.sub(pattern, replacement, content)
# Replace max_workers hardcoded value
pattern2 = r'with ThreadPoolExecutor\(max_workers=4\) as executor:'
replacement2 = 'with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS or min(32, os.cpu_count() + 4)) as executor:'
new_content = re.sub(pattern2, replacement2, new_content)
with open('ingest.py', 'w') as f:
    f.write(new_content)
