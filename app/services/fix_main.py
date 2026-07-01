import sys
sys.stdout.reconfigure(encoding="utf-8")

path = "c:/Users/14040/Desktop/campus-idle-fullstack/main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Add AsyncSession import
old_import = "from sqlalchemy.ext.asyncio import AsyncSession"
if old_import not in c:
    c = c.replace(
        "from app.core.database import init_db, close_db, async_session_factory",
        "from app.core.database import init_db, close_db, async_session_factory\nfrom sqlalchemy.ext.asyncio import AsyncSession"
    )

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("main.py import fixed")
