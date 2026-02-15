import re
with open('search.py', 'r') as f:
    lines = f.readlines()
new_lines = []
for line in lines:
    new_lines.append(line)
    if line.startswith('import ollama'):
        idx = len(new_lines) - 1
        new_lines.insert(idx + 1, 'import logging\n')
        new_lines.insert(idx + 2, 'from tenacity import retry, stop_after_attempt, wait_exponential\n')
        new_lines.insert(idx + 3, '\n')
        new_lines.insert(idx + 4, 'logger = logging.getLogger(__name__)\n')
        new_lines.insert(idx + 5, '\n')
# Replace print statements
for i in range(len(new_lines)):
    line = new_lines[i]
    if 'print(' in line:
        if 'Error' in line or 'error' in line:
            new_lines[i] = line.replace('print(', 'logger.error(')
        else:
            new_lines[i] = line.replace('print(', 'logger.info(')
# Add retry to get_embedding
for i, line in enumerate(new_lines):
    if 'def get_embedding(self, text: str) -> List[float]:' in line:
        new_lines.insert(i, '    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))\n')
        break
# Add retry to extract_entities (optional)
for i, line in enumerate(new_lines):
    if 'def extract_entities(self, query: str) -> List[str]:' in line:
        new_lines.insert(i, '    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))\n')
        break
# Add retry to generate_answer
for i, line in enumerate(new_lines):
    if 'def generate_answer(self, query: str, context: str) -> str:' in line:
        new_lines.insert(i, '    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))\n')
        break
with open('search.py', 'w') as f:
    f.writelines(new_lines)
