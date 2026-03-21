# 时间记录系统使用指南

> 其他工作空间调用时间数据时，请先阅读本文档

## 快速访问

### 方式 1: HTTP API（推荐）

API 服务器地址：`http://localhost:8080`

```python
import requests

# 获取当前任务状态
resp = requests.get("http://localhost:8080/api/time/current")
# 返回: {"status": "running", "task_name": "调ai", "start_time": "..."}

# 获取统计报表
resp = requests.get("http://localhost:8080/api/time/report?period=today")
# period 可选: today, week, month, total

# 获取历史记录
resp = requests.get("http://localhost:8080/api/time/history?date=2026-03-21")

# 开始任务
resp = requests.post("http://localhost:8080/api/time/start", 
    json={"task": "工作"})

# 停止任务
resp = requests.post("http://localhost:8080/api/time/stop")
```

### 方式 2: 直接读取文件（只读！）

```python
import json
import pandas as pd

# 当前任务
with open("/home/operit/current_task.json") as f:
    current = json.load(f)

# 时间记录
df = pd.read_csv("/home/operit/time_log.csv")

# App 使用记录
with open("/home/operit/app_usage_log.json") as f:
    app_usage = json.load(f)
```

## 重要规则

1. **不要修改代码文件** - `/home/operit/*.py` 是运行中的服务
2. **不要删除数据文件** - `time_log.csv` 是历史记录
3. **写操作用 API** - 开始/停止任务请用 API，不要直接改文件

## 项目结构

```
/home/operit/                    # 运行目录（不要乱改）
├── time_tracker.py              # 核心逻辑
├── app_monitor_v2.py            # App 监控
├── watchdog_monitor.py          # 看门狗
├── api_server.py                # API 服务器 (端口 8080)
├── start_task.py                # 任务切换入口
├── time_log.csv                 # 时间记录数据
├── current_task.json            # 当前任务状态
├── app_usage_log.json           # App 使用记录
└── TIME_TRACKER_GUIDE.md        # 本文档

/home/operit/time-tracker/       # Git 仓库（版本控制）
├── scripts/                     # 脚本副本
├── config/                      # 配置文件
└── docs/                        # 文档

/data/user/0/.../workspace/...   # Web 工作区（预览界面）
├── index.html                   # Web 界面
└── web_status.json              # 实时状态副本
```

## 服务状态检查

```bash
# 检查服务是否运行
pgrep -af "api_server.py"        # API 服务器
pgrep -af "watchdog_monitor.py"  # 看门狗
pgrep -af "app_monitor_v2.py"    # App 监控

# 心跳状态
cat /home/operit/watchdog_heartbeat.txt
```

## 常用命令

```bash
# 查看今日统计
python3 /home/operit/time_tracker.py report today

# 开始任务
python3 /home/operit/start_task.py "任务名"

# 停止当前任务
python3 /home/operit/start_task.py stop
```

## 注意事项

- Proot 环境无法执行 Android 命令（如 `am`, `dumpsys`）
- 时间数据单位为秒
- 任务名称支持中英文和同义词匹配
- API 已支持 CORS，可跨域访问

---
最后更新: 2026-03-21
