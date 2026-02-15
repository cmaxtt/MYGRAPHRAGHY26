import re
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()
# Add import config after other imports
if 'from config import settings' not in content:
    content = re.sub(r'from search import SearchEngine', 'from search import SearchEngine\nfrom config import settings', content)
# Replace hardcoded model names with settings
content = content.replace('_check_ollama_model("nomic-embed-text")', f'_check_ollama_model(settings.EMBED_MODEL)')
content = content.replace('_check_ollama_model("gpt-oss:20b-cloud")', f'_check_ollama_model(settings.LLM_MODEL)')
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
