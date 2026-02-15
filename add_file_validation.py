import re
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()
# Find the button block
pattern = r'(\s+if st\.button\("🚀 Process Documents"\) and uploaded_files:\s*\n\s+with st\.status\("Processing documents\.\.\.", expanded=True\) as status:)'
def replace(match):
    indent = match.group(1).split('\n')[0]  # get the whitespace before if
    return match.group(1) + f'\n{indent}    # Validate files\n{indent}    valid_files = []\n{indent}    for uploaded_file in uploaded_files:\n{indent}        # Check extension\n{indent}        ext = os.path.splitext(uploaded_file.name)[1].lower()\n{indent}        if ext not in [".pdf", ".docx", ".xlsx", ".csv", ".txt"]:\n{indent}            st.warning(f"Skipping {{uploaded_file.name}}: unsupported extension {{ext}}")\n{indent}            continue\n{indent}        # Check size (max 100 MB)\n{indent}        max_size = 100 * 1024 * 1024\n{indent}        if uploaded_file.size > max_size:\n{indent}            st.warning(f"Skipping {{uploaded_file.name}}: file size exceeds 100 MB")\n{indent}            continue\n{indent}        valid_files.append(uploaded_file)\n{indent}    if not valid_files:\n{indent}        st.error("No valid files to process")\n{indent}        return\n{indent}    # Process valid files\n{indent}    uploaded_files = valid_files\n'
new_content = re.sub(pattern, replace, content, flags=re.DOTALL)
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
