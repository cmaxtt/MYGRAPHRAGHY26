import re
with open('search.py', 'r') as f:
    content = f.read()
# Add import config after imports
content = re.sub(r'from db import Database', 'from db import Database\nfrom config import settings', content)
# Replace embed_model and llm_model assignments
pattern = r'self\.embed_model = "nomic-embed-text"\s*\n\s*self\.llm_model = "gpt-oss:20b-cloud"'
replacement = 'self.embed_model = settings.EMBED_MODEL\n        self.llm_model = settings.LLM_MODEL'
new_content = re.sub(pattern, replacement, content)
# Replace top_k default value in hybrid_search (line 12)
pattern2 = r'def hybrid_search\(self, query: str, top_k: int = 5\) -> Dict:'
replacement2 = 'def hybrid_search(self, query: str, top_k: int = settings.VECTOR_TOP_K) -> Dict:'
new_content = re.sub(pattern2, replacement2, new_content)
# Replace top_k parameter in vector_search call (line 15) - keep as variable
# No need to change
with open('search.py', 'w') as f:
    f.write(new_content)
