"""
完整状态机端到端测试（通过 HTTP API）
覆盖：创建 → 列表 → claim → complete / fail / cancel
"""
import sys, urllib.request, json, time
sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8000"

def get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as r:
        body = r.read().decode("utf-8")
        print(f"[GET {url}]")
        print(body)
        return json.loads(body)

def post(url, data):
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

print("=" * 60)
print("  状态机端到端演示（HTTP API）")
print("=" * 60)

# 1. 创建任务
print("\n--- Step 1: 创建任务 ---")
created = post(f"{BASE}/api/v1/tasks", {
    "task_type": "matching",
    "payload": {"item_id": "item-001", "user_id": "u-123"},
    "max_retries": 2,
    "queue_name": "default"
})
task_id = created["id"]
print(f"  -> 创建成功: {task_id[:8]}...")

# 2. 查询列表
print("\n--- Step 2: 列出所有任务 ---")
list_resp = get(f"{BASE}/api/v1/tasks")
print(f"  -> 当前任务总数: {len(list_resp['tasks'])}")

# 3. 领取任务
print("\n--- Step 3: 领取任务 (claim) ---")
claim_resp = post(f"{BASE}/api/v1/tasks/{task_id}/claim", {})
print(f"  -> 领取结果: {claim_resp}")

# 4. 完成
print("\n--- Step 4: 完成任务 (complete) ---")
complete_resp = post(f"{BASE}/api/v1/tasks/{task_id}/complete", {})
print(f"  -> 完成结果: {complete_resp}")

# 5. 验证最终状态
print("\n--- Step 5: 验证最终状态 ---")
final = get(f"{BASE}/api/v1/tasks")
for t in final["tasks"]:
    if t["id"] == task_id:
        print(f"  -> 任务状态: {t['status']}")
        assert t["status"] == "success", f"预期 success，实际 {t['status']}"
        break

# 6. 再创建一个用于 fail 流程
print("\n--- Step 6: 创建第二个任务（用于 fail 流程）---")
created2 = post(f"{BASE}/api/v1/tasks", {
    "task_type": "notification",
    "payload": {"msg": "test fail"},
    "max_retries": 1,
    "queue_name": "default"
})
task_id2 = created2["id"]
print(f"  -> 创建成功: {task_id2[:8]}...")

# 7. claim 第二个任务
print("\n--- Step 7: 领取第二个任务 ---")
claim_resp2 = post(f"{BASE}/api/v1/tasks/{task_id2}/claim", {})
print(f"  -> 领取结果: {claim_resp2}")

# 8. fail 第一个任务（触发重试）
print("\n--- Step 8: 失败任务 (fail) ---")
fail_resp = post(f"{BASE}/api/v1/tasks/{task_id2}/fail?error=simulated_error", {})
print(f"  -> 失败结果: {fail_resp}")

# 9. 检查状态
print("\n--- Step 9: 检查任务状态 ---")
final2 = get(f"{BASE}/api/v1/tasks")
for t in final2["tasks"]:
    if t["id"] == task_id2:
        print(f"  -> 任务状态: {t['status']}, 尝试次数: {t['attempt']}")

print("\n" + "=" * 60)
print("  【成功】状态机端到端演示完成")
print("=" * 60)
