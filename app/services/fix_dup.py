import sys
sys.stdout.reconfigure(encoding='utf-8')

path = 'c:/Users/14040/Desktop/campus-idle-fullstack/app/services/task_service.py'

with open(path, 'rb') as f:
    data = f.read()

text = data.decode('utf-8')

# Find the duplicate: old header starts after the first complete "return task" block
marker = '"""\nTaskService — 异步任务状态机核心\n实现任务创建、领取(CAS)、完成、失败(带重试)、取消、重试调度\n"""'
idx = text.find(marker)
if idx > 0:
    # Keep only content before the duplicate
    text = text[:idx]
    # Remove trailing whitespace lines
    text = text.rstrip() + '\n'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'Fixed: removed duplicate, file now {len(text)} chars')
else:
    print('No duplicate marker found')
