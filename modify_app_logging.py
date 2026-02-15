import re
with open('app.py', 'r') as f:
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
# Replace generic except: lines
for i, line in enumerate(new_lines):
    if 'except:' in line and '#' not in line.split('except:')[0]:
        # Find the line number, need to see context
        # We'll replace with 'except Exception as e:' and add logging
        # This is a bit complex; we'll do a simpler approach: replace the whole block manually later
        pass
# Let's do manual replacements using regex
content = ''.join(new_lines)
# Replace "except:" with "except Exception as e:"
content = re.sub(r'except:', 'except Exception as e:', content)
# Add logger.error after each st.error? We'll keep as is for now.
with open('app.py', 'w') as f:
    f.write(content)
