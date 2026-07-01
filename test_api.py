import sys, asyncio, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "c:/Users/14040/Desktop/campus-idle-fullstack")

import httpx

BASE = "http://localhost:8000"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. health
        r = await client.get(f"{BASE}/health")
        print(f"[GET /health] {r.status_code} {r.json()}")

        # 2. create task
        payload = {
            "task_type": "matching",
            "payload": {"item_id": "abc"},
            "max_retries": 2,
            "queue_name": "test"
        }
        r = await client.post(f"{BASE}/api/v1/tasks", json=payload)
        print(f"[POST /api/v1/tasks] {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  id={data['id']} status={data['status']}")
            task_id = data["id"]
        else:
            print(f"  ERROR: {r.text}")
            return

        # 3. list tasks
        r = await client.get(f"{BASE}/api/v1/tasks")
        print(f"[GET /api/v1/tasks] {r.status_code}")
        if r.status_code == 200:
            tasks = r.json()["tasks"]
            print(f"  total={len(tasks)}")
            for t in tasks:
                print(f"    {t['id'][:8]}... type={t['type']} status={t['status']} attempt={t['attempt']}")

        # 4. claim task
        r = await client.post(f"{BASE}/api/v1/tasks/{task_id}/claim")
        print(f"[POST /api/v1/tasks/{{id}}/claim] {r.status_code} {r.json()}")

        # 5. complete task
        r = await client.post(f"{BASE}/api/v1/tasks/{task_id}/complete")
        print(f"[POST /api/v1/tasks/{{id}}/complete] {r.status_code} {r.json()}")

        # 6. fail task
        r = await client.post(f"{BASE}/api/v1/tasks/{task_id}/fail?error=test_error")
        print(f"[POST /api/v1/tasks/{{id}}/fail] {r.status_code} {r.json()}")

        print("\n[OK] 所有 API 测试通过")

if __name__ == "__main__":
    asyncio.run(main())
