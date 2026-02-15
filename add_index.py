import re
with open('db.py', 'r') as f:
    content = f.read()
# Find the CREATE TABLE block and insert index creation after it
pattern = r'(\s+cur\.execute\("""\n\s*CREATE TABLE IF NOT EXISTS chunks \([^)]+\);\n\s*""")'
def replace(match):
    return match.group(1) + '\n' + ' ' * 20 + 'cur.execute("CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops)")'
new_content = re.sub(pattern, replace, content, flags=re.DOTALL)
with open('db.py', 'w') as f:
    f.write(new_content)
