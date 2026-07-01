import sys
sys.stdout.reconfigure(encoding="utf-8")

p = "c:/Users/14040/Desktop/campus-idle-fullstack/test_api.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("http://localhost:8000", "http://localhost:8000")

with open(p, "w", encoding="utf-8") as f:
    f.write(c)
print("fixed")
