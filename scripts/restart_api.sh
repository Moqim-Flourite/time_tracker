#!/bin/bash
cd /home/operit
pkill -f api_server.py 2>/dev/null
sleep 1
nohup python3 api_server.py > /dev/null 2>&1 &
echo "API服务器已重启"
echo "访问 http://localhost:8000 查看网页界面"