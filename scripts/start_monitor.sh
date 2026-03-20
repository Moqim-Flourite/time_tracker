#!/bin/bash
# 启动时间记录助手所有服务 + Prime智能系统
# 用于Proot启动时自动运行

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 启动系统服务..."

# 等待系统稳定
sleep 3

# 1. 启动cron服务（定时任务基础）
echo "启动cron服务..."
service cron start 2>/dev/null || service crond start 2>/dev/null || true

# 2. 启动API服务器
echo "启动API服务器..."
cd /home/operit
if ! pgrep -f "api_server.py" > /dev/null; then
    nohup python3 api_server.py > /tmp/api_server.log 2>&1 &
    sleep 1
    echo "✅ API服务器已启动"
else
    echo "✅ API服务器已在运行"
fi

# 3. 启动Proot端监控
echo "启动Proot监控..."
if ! pgrep -f "app_monitor_v2.py _run" > /dev/null; then
    nohup python3 /home/operit/app_monitor_v2.py _run >> /home/operit/app_monitor_v2.log 2>&1 &
    sleep 2
    echo "✅ Proot监控已启动"
else
    echo "✅ Proot监控已在运行"
fi

# 4. 尝试启动Android端监控脚本（需要shizuku权限）
echo "检查Android监控..."
if [ -f /sdcard/OperitNotifications/current_app.txt ]; then
    AGE=$(($(date +%s) - $(stat -c %Y /sdcard/OperitNotifications/current_app.txt 2>/dev/null || echo 0)))
    if [ $AGE -gt 300 ]; then
        echo "⚠️ Android监控可能已停止（文件${AGE}秒未更新）"
        # 尝试重启（需要shizuku）
        sh /sdcard/OperitNotifications/monitor_app.sh 2>/dev/null &
        echo "已尝试重启Android监控"
    else
        echo "✅ Android监控正常"
    fi
else
    echo "⚠️ current_app.txt 不存在"
fi

# 5. 启动Prime智能系统
echo "启动Prime智能系统..."
if ! pgrep -f "prime_watchdog.py --run" > /dev/null; then
    nohup python3 /home/operit/prime/prime_watchdog.py --run >> /home/operit/prime/logs/prime_watchdog.log 2>&1 &
    sleep 3
    echo "✅ Prime智能系统已启动"
else
    echo "✅ Prime智能系统已在运行"
fi

# 输出状态
echo ""
echo "========== 服务状态 =========="
echo "cron:     $(pgrep -x cron > /dev/null && echo '✅ 运行中' || echo '❌ 未运行')"
echo "API:      $(pgrep -f 'api_server.py' > /dev/null && echo '✅ 运行中' || echo '❌ 未运行')"
echo "监控:     $(pgrep -f 'app_monitor_v2.py _run' > /dev/null && echo '✅ 运行中' || echo '❌ 未运行')"
echo "Prime:    $(pgrep -f 'prime_watchdog.py --run' > /dev/null && echo '✅ 运行中' || echo '❌ 未运行')"
echo "================================"
echo ""
echo "💡 看门狗会每分钟自动检查并重启异常服务"
