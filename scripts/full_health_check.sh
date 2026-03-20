#!/bin/bash
# 完整健康检查脚本
echo "========== 时间记录助手健康检查 =========="
echo "检查时间: $(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. API服务器
echo "【1】API服务器"
if pgrep -f "python3 api_server.py" > /dev/null; then
    echo "  ✅ 运行中"
else
    echo "  ❌ 已停止"
fi

# 2. 监控服务
echo "【2】Proot监控服务"
if [ -f /home/operit/app_monitor_v2.pid ]; then
    PID=$(cat /home/operit/app_monitor_v2.pid)
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "  ✅ 运行中 (PID: $PID)"
    else
        echo "  ❌ PID文件存在但进程不存在"
    fi
else
    echo "  ❌ PID文件不存在"
fi

# 3. 当前任务状态
echo "【3】当前任务"
if [ -f /home/operit/current_task.json ]; then
    TASK=$(cat /home/operit/current_task.json)
    TASK_NAME=$(echo "$TASK" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('task_name','无'))" 2>/dev/null)
    START_TIME=$(echo "$TASK" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('start_time',''))" 2>/dev/null)
    RUNNING=$(echo "$TASK" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('running',False))" 2>/dev/null)
    LOCKED=$(echo "$TASK" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('locked',False))" 2>/dev/null)
    
    if [ "$RUNNING" = "True" ] && [ -n "$START_TIME" ]; then
        ELAPSED=$(python3 -c "
import json
from datetime import datetime
with open('/home/operit/current_task.json') as f:
    d = json.load(f)
if d.get('running') and d.get('start_time'):
    for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']:
        try:
            start = datetime.strptime(d['start_time'], fmt)
            now = datetime.now()
            secs = int((now - start).total_seconds())
            hours = secs // 3600
            mins = (secs % 3600) // 60
            print(f'{hours}h {mins}m')
            break
        except: pass
" 2>/dev/null)
        echo "  任务: $TASK_NAME"
        echo "  开始: $START_TIME"
        echo "  时长: $ELAPSED"
        [ "$LOCKED" = "True" ] && echo "  🔒 已锁定（监控暂停）"
    else
        echo "  无运行中任务"
    fi
else
    echo "  ❌ 状态文件不存在"
fi

# 4. 日志文件检查
echo "【4】日志文件"
if [ -f /home/operit/time_log.csv ]; then
    LAST_RECORD=$(tail -1 /home/operit/time_log.csv)
    LAST_TIME=$(echo "$LAST_RECORD" | cut -d',' -f3 | cut -d'.' -f1)
    echo "  最后记录: $LAST_TIME"
    RECORDS_TODAY=$(grep "$(TZ='Asia/Shanghai' date '+%Y-%m-%d')" /home/operit/time_log.csv 2>/dev/null | wc -l)
    echo "  今日记录数: $RECORDS_TODAY"
else
    echo "  ❌ 日志文件不存在"
fi

# 5. web_status同步检查 (工作区)
echo "【5】web_status同步"
CT_TIME=$(cat /home/operit/current_task.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('start_time',''))" 2>/dev/null)
WORKSPACE_WS="/data/user/0/com.ai.assistance.operit/files/workspace/ea9e1ec2-3f82-46e4-9c7a-a251ac5c747e/web_status.json"
if [ -f "$WORKSPACE_WS" ]; then
    WS_WS_TIME=$(cat "$WORKSPACE_WS" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('timestamp',''))" 2>/dev/null)
    WS_TASK=$(cat "$WORKSPACE_WS" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('task_name',''))" 2>/dev/null)
    echo "  任务: $WS_TASK"
    echo "  时间: $WS_WS_TIME"
    if [ -n "$WS_WS_TIME" ] && [ "$WS_WS_TIME" = "$CT_TIME" ]; then
        echo "  ✅ 同步"
    else
        echo "  ⚠️ 可能不同步"
    fi
else
    echo "  ❌ 文件不存在"
fi

# 6. Android端监控脚本
echo "【6】Android端监控脚本"
MONITOR_LOG="/sdcard/OperitNotifications/monitor_app.log"
CURRENT_APP="/sdcard/OperitNotifications/current_app.txt"
if [ -f "$MONITOR_LOG" ]; then
    LAST_START=$(tail -1 "$MONITOR_LOG")
    echo "  最后启动: $LAST_START"
else
    echo "  ❌ 监控日志不存在"
fi

if [ -f "$CURRENT_APP" ]; then
    APP_CONTENT=$(cat "$CURRENT_APP")
    APP_TIME=$(stat -c %Y "$CURRENT_APP" 2>/dev/null)
    NOW_TIME=$(date +%s)
    AGE=$((NOW_TIME - APP_TIME))
    if [ $AGE -gt 120 ]; then
        echo "  ⚠️ current_app.txt 已过期 (${AGE}秒前)"
        echo "     内容: $APP_CONTENT"
    else
        echo "  ✅ current_app.txt 正常 (${AGE}秒前)"
        echo "     内容: $APP_CONTENT"
    fi
else
    echo "  ❌ current_app.txt 不存在"
fi

# 7. 工作流状态
echo "【7】工作流检测"
WORKFLOW_LOG="/home/operit/app_usage_log.json"
if [ -f "$WORKFLOW_LOG" ]; then
    LAST_WF=$(tail -1 "$WORKFLOW_LOG" | python3 -c "
import sys,json
try:
    line = sys.stdin.read().strip()
    if line.endswith(','): line = line[:-1]
    d = json.loads(line)
    print(d.get('timestamp',''))
except: pass
" 2>/dev/null)
    [ -n "$LAST_WF" ] && echo "  最后记录: $LAST_WF" || echo "  无记录"
else
    echo "  ❌ 工作流日志不存在"
fi

echo ""
echo "========== 检查完成 =========="
