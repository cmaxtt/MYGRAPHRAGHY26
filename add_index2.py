with open('db.py', 'r') as f:
    lines = f.readlines()
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)
    # Look for the CREATE TABLE line (contains CREATE TABLE IF NOT EXISTS chunks)
    if 'CREATE TABLE IF NOT EXISTS chunks' in line:
        # We are at the line with CREATE TABLE... but inside triple quotes.
        # Need to find the line that ends with '""")' after this.
        # Let's just skip until we find the line that ends with '""")'
        # We'll continue adding lines until we find it.
        j = i + 1
        while j < len(lines) and not lines[j].strip().endswith('""")'):
            new_lines.append(lines[j])
            j += 1
        if j < len(lines):
            # Add the line with the closing triple quotes
            new_lines.append(lines[j])
            # Insert our new line after this line
            indent = ' ' * 20  # 20 spaces matching the indentation of cur.execute
            new_lines.append(indent + 'cur.execute("CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops)")\n')
            i = j
    i += 1
with open('db.py', 'w') as f:
    f.writelines(new_lines)
