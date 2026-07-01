import sys
sys.stdout.reconfigure(encoding='utf-8')

path = 'c:/Users/14040/Desktop/campus-idle-fullstack/app/models/task.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the column types for SQLite JSON compatibility
old = 'JSONB().with_variant(Text, "sqlite")'
new = 'SA_JSON().with_variant(JSONB, "postgresql")'
count = content.count(old)
content = content.replace(old, new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Replaced {count} occurrences")
