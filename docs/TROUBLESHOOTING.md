# 故障排查指南

## 问题1: Web界面显示的任务与实际不符

### 症状
- Web界面显示"调ai"或其他旧任务，但实际已切换到其他App
- `current_task.json` 与日志 `time_log.csv` 不同步
- API返回的任务与实际不符

### 原因分析
1. **Proot崩溃导致状态不同步**
   - Operit App崩溃/更新后，Proot容器重启
   - Python进程全部消失，但状态文件可能残留旧数据
   - `current_task.json` 可能记录着崩溃前的任务

2. **`current_app.txt` 停止更新**
   - 该文件由Operit App的工作流定时写入前台App信息
   - Operit崩溃或Shizuku断开后，工作流停止运行
   - 监控脚本读取到的是旧数据，无法检测真实的App切换

### 诊断命令
```bash
# 检查当前前台App
dumpsys window 2>/dev/null | grep -E "mCurrentFocus" | head -1

# 检查current_app.txt内容和时间
cat /sdcard/OperitNotifications/current_app.txt
ls -la /sdcard/OperitNotifications/current_app.txt

# 检查current_task.json
cat /home/operit/current_task.json

# 检查最新日志记录
tail -5 /home/operit/time_log.csv

# 检查监控日志
tail -10 /home/operit/app_monitor_v2.log
```

### 解决方法

#### 方法1: 手动同步当前App
```bash
# 通过shell更新current_app.txt
echo "com.包名" > /sdcard/OperitNotifications/current_app.txt

# 常见App包名
# Operit: com.ai.assistance.operit
# 微信: com.tencent.mm
# 多邻国: com.duolingo
# QQ: com.tencent.mobileqq
```

#### 方法2: 手动切换任务
```bash
python3 /home/operit/start_task.py "任务名"
```

#### 方法3: 重启监控服务
```bash
pkill -f app_monitor_v2.py
python3 /home/operit/app_monitor_v2.py start
```

---

## 问题2: Proot频繁崩溃/重启

### 症状
- `uptime` 显示只有几分钟
- Python进程消失
- 看门狗自动恢复服务

### 原因分析
- Operit App发生ANR (Application Not Responding)
- 主线程阻塞超过5秒，系统强制重启App
- Proot容器随之重启

### 诊断命令
```bash
# 查看Proot运行时间
uptime

# 检查进程状态
ps aux | grep python | grep -v grep

# 查看崩溃恢复日志
cat /home/operit/crash_recovery.log | tail -20

# 查看Android ANR日志 (需要root/shizuku)
dumpsys dropbox --print 2>/dev/null | grep -A 20 "anr"
```

### 解决方法
1. **自动恢复**: 看门狗和crontab会自动恢复服务
2. **减少ANR触发**:
   - 避免在Operit中同时运行多个重任务
   - 将Operit加入后台白名单
   - 关闭省电策略对Operit的限制
3. **向Operit开发者反馈ANR问题**

---

## 问题3: 监控不检测App切换

### 症状
- 打开不同App，任务不自动切换
- `app_monitor_v2.log` 停止更新
- `current_app.txt` 内容长时间不变

### 原因分析
1. Operit工作流未运行
2. Shizuku服务断开
3. 监控进程卡住

### 诊断命令
```bash
# 检查监控进程
ps aux | grep app_monitor | grep -v grep

# 检查监控日志最新记录
tail -5 /home/operit/app_monitor_v2.log

# 检查current_app.txt更新时间
ls -la /sdcard/OperitNotifications/current_app.txt
```

### 解决方法
```bash
# 重启监控
pkill -f app_monitor_v2.py
python3 /home/operit/app_monitor_v2.py start

# 检查Operit工作流是否启用
# 在Operit App中检查自动任务/工作流设置

# 重启Shizuku (如果需要)
```

---

## 问题4: Web界面数据不更新

### 症状
- Web界面显示旧数据
- 刷新页面后数据不变

### 原因分析
有两个web_status.json文件:
- `/home/operit/web_status.json` - 旧位置，可能不更新
- 工作区路径 - 正常更新

### 诊断命令
```bash
# 检查两个文件的更新时间
ls -la /home/operit/web_status.json
ls -la /data/user/0/com.ai.assistance.operit/files/workspace/*/web_status.json

# 检查API返回
curl -s http://localhost:8080/api/time/current
```

### 解决方法
- 确保Web界面读取的是工作区路径的文件
- 手动触发更新: `python3 /home/operit/start_task.py 当前任务`

---

## 快速恢复脚本

保存为 `/home/operit/fix_monitor.sh`:
```bash
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
```

---

## 相关文件路径

| 文件 | 路径 | 说明 |
|------|------|------|
| 时间日志 | `/home/operit/time_log.csv` | 所有任务记录 |
| 当前任务 | `/home/operit/current_task.json` | 当前运行的任务 |
| 监控配置 | `/home/operit/app_monitor_config.json` | 监控参数配置 |
| 监控日志 | `/home/operit/app_monitor_v2.log` | 监控运行日志 |
| App信息 | `/sdcard/OperitNotifications/current_app.txt` | 前台App包名 |
| Web状态 | 工作区路径/web_status.json | Web界面数据 |
| 崩溃恢复 | `/home/operit/crash_recovery.log` | 崩溃恢复记录 |
| 看门狗心跳 | `/home/operit/watchdog_heartbeat.json` | 服务健康状态 |

---

*最后更新: 2026-03-22*
