import re
with open('backend/app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# remove DB_CONFIG block entirely
code = re.sub(r'DB_CONFIG = \{.*?\n\}', '', code, flags=re.DOTALL)

with open('backend/app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('DB_CONFIG removed!')
