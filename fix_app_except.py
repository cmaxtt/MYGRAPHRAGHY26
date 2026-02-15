import re
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()
# Replace generic except:
content = re.sub(r'except:', 'except Exception as e:', content)
# Add logging after each st.error? We'll just add logger.error before st.error
# Find pattern: st.error(f"Error ...")
# We'll add logger.error(e) before st.error lines where e is variable.
# Let's do simple: after each st.error line that contains {e}, add logger.error(e)
# Actually we can add logging in the except block.
# Let's find the except block and add logger.error("Could not connect to Knowledge Graph for stats", exc_info=e)
# We'll do manual replacement for the specific block.
# We'll replace from line "except:" to "st.error(...)" with additional logging.
# Use regex with multiline.
pattern = r'(except Exception as e:\s*\n\s*st\.error\("Could not connect to Knowledge Graph for stats"\))'
replacement = r'\1\n        logger.error("Could not connect to Knowledge Graph for stats", exc_info=e)'
content = re.sub(pattern, replacement, content)
# Also add logger.error for resetting error
pattern2 = r'(except Exception as e:\s*\n\s*st\.error\(f"Error resetting: {e}"\))'
replacement2 = r'\1\n        logger.error("Error resetting database", exc_info=e)'
content = re.sub(pattern2, replacement2, content)
# Also add logger.error for error during search
pattern3 = r'(except Exception as e:\s*\n\s*st\.error\(f"Error during search: {e}"\))'
replacement3 = r'\1\n        logger.error("Error during search", exc_info=e)'
content = re.sub(pattern3, replacement3, content)
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
