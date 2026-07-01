import sys
sys.stdout.reconfigure(encoding="utf-8")

path = "c:/Users/14040/Desktop/campus-idle-fullstack/main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Replace emojis with ASCII-safe markers
replacements = [
    ("✅", "[OK]"),
    ("⚠️", "[WARN]"),
    ("⏰", "[SCHED]"),
]

for old, new in replacements:
    c = c.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print(f"Fixed {len(replacements)} emoji replacements")
