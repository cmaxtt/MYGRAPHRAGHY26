import re
with open('db.py', 'r') as f:
    content = f.read()
# Replace the block of environment variable reading with import config
pattern = r'load_dotenv\(\)\s*\n\s*# PostgreSQL configuration\s*\nPG_HOST = os\.getenv\("[^"]+", "[^"]*"\)\s*\nPG_PORT = os\.getenv\("[^"]+", "[^"]*"\)\s*\nPG_USER = os\.getenv\("[^"]+", "[^"]*"\)\s*\nPG_PWD = os\.getenv\("[^"]+", "[^"]*"\)\s*\nPG_DB = os\.getenv\("[^"]+", "[^"]*"\)\s*\n\s*# Neo4j configuration\s*\nNEO4J_URI = os\.getenv\("[^"]+", "[^"]*"\)\s*\nNEO4J_USER = os\.getenv\("[^"]+", "[^"]*"\)\s*\nNEO4J_PWD = os\.getenv\("[^"]+", "[^"]*"\)'
replacement = '''load_dotenv()

# Configuration
from config import settings

# PostgreSQL configuration
PG_HOST = settings.PG_HOST
PG_PORT = settings.PG_PORT
PG_USER = settings.PG_USER
PG_PWD = settings.PG_PWD
PG_DB = settings.PG_DB

# Neo4j configuration
NEO4J_URI = settings.NEO4J_URI
NEO4J_USER = settings.NEO4J_USER
NEO4J_PWD = settings.NEO4J_PWD'''
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
with open('db.py', 'w') as f:
    f.write(new_content)
