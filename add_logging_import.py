import re
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
new_lines = []
for line in lines:
    new_lines.append(line)
    if line.startswith('import streamlit as st'):
        idx = len(new_lines) - 1
        new_lines.insert(idx + 1, 'import logging\n')
        new_lines.insert(idx + 2, 'logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")\n')
        new_lines.insert(idx + 3, 'logger = logging.getLogger(__name__)\n')
        new_lines.insert(idx + 4, '\n')
        break
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
