#!/bin/bash
# Prime 智能系统启动脚本
# 启动整个Prime系统（心跳/调度器/意识层/学习引擎）

cd /home/operit

# 检查Prime看门狗是否运行
if pgrep -f "prime_watchdog.py --run" > /dev/null; then
    echo "Prime系统已在运行"
    # 显示状态
    python3 /home/operit/prime/prime_watchdog.py --status
    exit 0
fi

# 启动Prime看门狗（它会自动管理所有服务）
echo "启动 Prime 智能系统..."
nohup python3 /home/operit/prime/prime_watchdog.py --run >> /home/operit/prime/logs/prime_watchdog.log 2>&1 &

sleep 3

# 显示状态
echo ""
python3 /home/operit/prime/prime_watchdog.py --status

echo ""
echo "Prime系统已启动 (看门狗PID: $!)"