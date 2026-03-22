#!/bin/bash
echo "🔧 检查并修复监控系统..."

# 1. 重启监控
pkill -f app_monitor_v2.py 2>/dev/null
sleep 1
python3 /home/operit/app_monitor_v2.py start

# 2. 获取当前前台App
CURRENT_APP=$(dumpsys window 2>/dev/null | grep -E "mCurrentFocus" | head -1 | grep -oP 'com\.[a-z0-9_.]+' | head -1)
if [ -n "$CURRENT_APP" ]; then
    echo "📱 当前App: $CURRENT_APP"
    echo "$CURRENT_APP" > /sdcard/OperitNotifications/current_app.txt
fi

# 3. 检查服务状态
echo "📊 服务状态:"
ps aux | grep -E "(api_server|app_monitor|watchdog)" | grep -v grep | awk '{print $11, "✅"}'

echo "✅ 修复完成"
