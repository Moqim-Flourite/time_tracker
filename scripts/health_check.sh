#!/bin/bash
# 时间记录助手 + Prime智能系统 健康检查脚本
# 检查并自动重启停止的服务

LOG_FILE="/home/operit/health_check.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

log() {
    echo "[$DATE] $1" >> "$LOG_FILE"
}

# 1. 检查API服务器
if ! pgrep -f "python3 api_server.py" > /dev/null; then
    log "API服务器已停止，正在重启..."
    cd /home/operit && nohup python3 api_server.py > /tmp/api_server.log 2>&1 &
    sleep 1
    if pgrep -f "python3 api_server.py" > /dev/null; then
        log "API服务器重启成功"
    else
        log "API服务器重启失败"
    fi
fi

# 2. 检查Proot监控服务
if [ -f /home/operit/app_monitor_v2.pid ]; then
    PID=$(cat /home/operit/app_monitor_v2.pid)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        log "Proot监控已停止，正在重启..."
        python3 /home/operit/app_monitor_v2.py start >> "$LOG_FILE" 2>&1
    fi
else
    log "PID文件不存在，正在启动监控..."
    python3 /home/operit/app_monitor_v2.py start >> "$LOG_FILE" 2>&1
fi

# 3. 检查Android端监控（通过检测current_app.txt更新时间）
APP_FILE="/sdcard/OperitNotifications/current_app.txt"
if [ -f "$APP_FILE" ]; then
    LAST_UPDATE=$(stat -c %Y "$APP_FILE" 2>/dev/null || stat -f %m "$APP_FILE" 2>/dev/null)
    NOW=$(date +%s)
    DIFF=$((NOW - LAST_UPDATE))
    if [ "$DIFF" -gt 120 ]; then
        log "警告: current_app.txt 超过${DIFF}秒未更新"
    fi
fi

# 4. 检查Prime智能系统
if ! pgrep -f "prime_watchdog.py --run" > /dev/null; then
    log "Prime看门狗未运行，正在启动..."
    nohup python3 /home/operit/prime/prime_watchdog.py --run >> /home/operit/prime/logs/prime_watchdog.log 2>&1 &
    sleep 3
    if pgrep -f "prime_watchdog.py --run" > /dev/null; then
        log "Prime智能系统启动成功"
    else
        log "Prime智能系统启动失败"
    fi
fi
