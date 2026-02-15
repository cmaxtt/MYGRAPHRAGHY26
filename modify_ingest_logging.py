import re
with open('ingest.py', 'r') as f:
    lines = f.readlines()
new_lines = []
for line in lines:
    new_lines.append(line)
    if line.startswith('import ollama'):
        # Insert after import ollama
        idx = len(new_lines) - 1
        new_lines.insert(idx + 1, 'import logging\n')
        new_lines.insert(idx + 2, 'from tenacity import retry, stop_after_attempt, wait_exponential\n')
        new_lines.insert(idx + 3, '\n')
        new_lines.insert(idx + 4, 'logger = logging.getLogger(__name__)\n')
        new_lines.insert(idx + 5, '\n')
# Now replace print statements with logger
for i in range(len(new_lines)):
    line = new_lines[i]
    if 'print(' in line:
        # Convert print(f"...") to logger.info or error
        if 'Error' in line or 'error' in line:
            new_lines[i] = line.replace('print(', 'logger.error(')
        else:
            new_lines[i] = line.replace('print(', 'logger.info(')
# Now add retry decorator to get_embedding and extract_triplets
# Find get_embedding method
for i, line in enumerate(new_lines):
    if 'def get_embedding(self, text: str) -> List[float]:' in line:
        # Insert decorator line before this line
        new_lines.insert(i, '    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))\n')
        break
# Find extract_triplets method
for i, line in enumerate(new_lines):
    if 'def extract_triplets(self, text: str) -> List[Dict]:' in line:
        new_lines.insert(i, '    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))\n')
        break
with open('ingest.py', 'w') as f:
    f.writelines(new_lines)
