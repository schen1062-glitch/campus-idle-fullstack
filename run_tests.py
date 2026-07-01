import sys, urllib.request, json
sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8000"

def get(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as r:
            body = r.read().decode("utf-8")
            print(f"[GET {url}]")
            print(body)
            return json.loads(body)
    except Exception as e:
        print(f"[GET {url}] ERROR: {e}")
        return None

def post(url, data):
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            body = r.read().decode("utf-8")
            print(f"[POST {url}]")
            print(body)
            return json.loads(body)
    except Exception as e:
        print(f"[POST {url}] ERROR: {e}")
        return None

print("=" * 60)
print("1. 健康检查")
print("=" * 60)
get(f"{BASE}/health")

print("\n" + "=" * 60)
print("2. 列出任务")
print("=" * 60)
get(f"{BASE}/api/v1/tasks")

print("\n" + "=" * 60)
print("3. 创建任务")
print("=" * 60)
post(f"{BASE}/api/v1/tasks", {
    "task_type": "matching",
    "payload": {"item_id": "abc"},
    "max_retries": 2,
    "queue_name": "test"
})

print("\n" + "=" * 60)
print("4. 再次列出任务")
print("=" * 60)
get(f"{BASE}/api/v1/tasks")
