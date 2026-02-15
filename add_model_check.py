import re
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()
# Add import ollama at top if not present
if 'import ollama' not in content:
    content = re.sub(r'import streamlit as st', 'import streamlit as st\nimport ollama', content)
# Define helper function before get_ingestor
helper = '''
def _check_ollama_model(model_name: str):
    """Check if Ollama model is available."""
    try:
        models = ollama.list()
        available = any(m["model"] == model_name for m in models["models"])
        if not available:
            logger.warning(f"Ollama model '{model_name}' not found. Please pull it.")
    except Exception as e:
        logger.error(f"Failed to check Ollama models: {e}")
'''
# Insert after logger = logging.getLogger(__name__)
if 'logger = logging.getLogger(__name__)' in content:
    content = content.replace('logger = logging.getLogger(__name__)', 'logger = logging.getLogger(__name__)\n' + helper)
# Modify get_ingestor function
pattern = r'(@st\.cache_resource\s*\ndef get_ingestor\(\):\s*\n\s*return Ingestor\(\s*\))'
def replace(match):
    indent = ' ' * 4
    return f'''@st.cache_resource
def get_ingestor():
{indent}# Check required Ollama models
{indent}_check_ollama_model("nomic-embed-text")
{indent}_check_ollama_model("gpt-oss:20b-cloud")
{indent}return Ingestor()'''
new_content = re.sub(pattern, replace, content, flags=re.DOTALL)
# Modify get_search_engine similarly
pattern2 = r'(@st\.cache_resource\s*\ndef get_search_engine\(\):\s*\n\s*return SearchEngine\(\s*\))'
def replace2(match):
    indent = ' ' * 4
    return f'''@st.cache_resource
def get_search_engine():
{indent}# Check required Ollama models
{indent}_check_ollama_model("nomic-embed-text")
{indent}_check_ollama_model("gpt-oss:20b-cloud")
{indent}return SearchEngine()'''
new_content = re.sub(pattern2, replace2, new_content, flags=re.DOTALL)
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
