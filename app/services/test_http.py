import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "c:/Users/14040/Desktop/campus-idle-fullstack")

import urllib.request
import json

BASE = "http://localhost:8000"

def get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        body = r.read().decode("utf-8")
        print(f"[GET {url}] {r.status} {body}")
        return json.loads(body)

def post(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        body = r.read().decode("utf-8")
        print(f"[POST {url}] {r.status} {body}")
        return json.loads(body)

print("=== 1. health ===")
get(f"{BASE}/health")

print("\n=== 2. list tasks (empty) ===")
get(f"{BASE}/api/v1/tasks")

print("\n=== 3. create task ===")
data = post(f"{BASE}/api/v1/tasks", {
    "task_type": "matching",
    "payload": {"item_id": "abc"},
    "max_retries": 2,
    "queue_name": "test"
})
task_id = data["id"]
print(f"  created id={task_id}")

print("\n=== 4. list tasks ===")
tasks = get(f"{BASE}/api/v1/tasks")
print(f"  total={len(tasks['tasks'])}")

print("\n=== 5. claim task ===")
post(f"{BASE}/api/v1/tasks/{task_id}/claim", {})

print("\n=== 6. complete task ===")
post(f"{BASE}/api/v1/tasks/{task_id}/complete", {})

print("\n[OK] 所有 API 测试通过")
