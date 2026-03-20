#!/usr/bin/env python3
"""
统一执行脚本：当用户说"开始xx"时，执行时间记录并更新Web界面
使用方法：python3 start_task.py <任务名> [备注]
示例：
  python3 start_task.py 洗漱 洗澡
  python3 start_task.py 刷手机 微信

任务锁定机制：
  - 锁定任务（LOCKED_TASKS）：吃饭、睡觉
  - 当用户手动切换到锁定任务时，自动监控暂停，直到用户说"吃完了/睡醒了"
  - 结束词（UNLOCK_PHRASES）：吃完了、睡醒了、不睡了、起醒了等
"""

import sys
import os
import json
import csv
from datetime import datetime, timedelta
import time
import re
import subprocess

# 需要锁定的任务列表（用户手动切换后，监控暂停）
LOCKED_TASKS = ["吃饭", "睡觉"]

# 解锁短语（用户说这些话时解锁监控）
UNLOCK_PHRASES = [
    "吃完了", "吃饱了", "吃好了", "吃完饭了",
    "睡醒了", "起床了", "醒了", "不睡了", "起醒了",
    "好了", "结束了", "完了"
]

def get_current_time():
    """获取当前时间，转换为北京时间（UTC+8）"""
    # 使用time模块获取时间戳
    timestamp = time.time()
    # 转换为datetime（UTC时间）
    utc_time = datetime.fromtimestamp(timestamp)
    # 转换为北京时间（UTC+8）
    beijing_time = utc_time + timedelta(hours=8)
    return beijing_time

def send_notification(title, content):
    """将通知写入队列，由Android端工作流发送（Proot无法直接调用cmd）"""
    NOTIFICATION_QUEUE = "/sdcard/OperitNotifications/notification_queue.json"
    NOTIFICATION_LOG = "/sdcard/OperitNotifications/notification_sent.log"
    
    try:
        # 读取现有队列
        queue = []
        if os.path.exists(NOTIFICATION_QUEUE):
            try:
                with open(NOTIFICATION_QUEUE, 'r', encoding='utf-8') as f:
                    queue = json.load(f)
            except:
                queue = []
        
        # 添加新通知到队列
        notification = {
            "title": title,
            "content": content,
            "time": datetime.now().isoformat()
        }
        queue.append(notification)
        
        # 只保留最近5条通知
        if len(queue) > 5:
            queue = queue[-5:]
        
        # 写入队列
        with open(NOTIFICATION_QUEUE, 'w', encoding='utf-8') as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        
        # 记录日志（表示已入队）
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        with open(NOTIFICATION_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] 入队: {title} - {content}\n")
        
        print(f"📢 通知已入队: {title}（等待工作流发送）")
        return True
    except Exception as e:
        print(f"⚠️ 通知入队失败: {e}")
        return False

def calculate_statistics():
    """读取CSV数据算出统计数据（支持跨日任务分摊）"""
    time_log_file = "/home/operit/time_log.csv"
    
    if not os.path.exists(time_log_file):
        return {
            "today": {"total_seconds": 0, "categories": {}},
            "week": {"total_seconds": 0, "categories": {}},
            "month": {"total_seconds": 0, "categories": {}},
            "year": {"total_seconds": 0, "categories": {}},
            "total": {"total_seconds": 0, "categories": {}}
        }
    
    stats = {
        "today": {"total_seconds": 0, "categories": {}},
        "week": {"total_seconds": 0, "categories": {}},
        "month": {"total_seconds": 0, "categories": {}},
        "year": {"total_seconds": 0, "categories": {}},
        "total": {"total_seconds": 0, "categories": {}}
    }
    
    now = get_current_time()  # 北京时间
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    year_start = today_start.replace(month=1, day=1)
    
    def parse_time(time_str):
        """解析时间字符串，返回北京时间datetime"""
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except:
                continue
        return None
    
    def add_to_stats(category, seconds, period):
        """添加统计"""
        if seconds > 0:
            stats[period]["total_seconds"] += seconds
            stats[period]["categories"][category] = stats[period]["categories"].get(category, 0) + seconds
    
    try:
        with open(time_log_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if '开始时间' not in row or '持续秒数' not in row or '类别' not in row:
                    continue
                
                try:
                    start_time = parse_time(row['开始时间'])
                    end_time = parse_time(row['结束时间'])
                    if not start_time or not end_time:
                        continue
                    
                    duration_seconds = int(row['持续秒数'])
                    category = row['类别']
                    
                    # 跳过异常数据
                    if duration_seconds < 0:
                        continue
                    
                    # 处理跨日任务：按天分摊时间
                    current_day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    while current_day_start < end_time:
                        # 当前天的结束时间（即下一天的0点）
                        next_day_start = current_day_start + timedelta(days=1)
                        
                        # 计算在当前天的时长
                        day_start = max(start_time, current_day_start)
                        day_end = min(end_time, next_day_start)
                        day_seconds = int((day_end - day_start).total_seconds())
                        
                        if day_seconds > 0:
                            # 判断属于哪个统计周期
                            day_date = current_day_start.date()
                            
                            # 今日
                            if day_date == today_start.date():
                                add_to_stats(category, day_seconds, "today")
                            
                            # 本周
                            if current_day_start >= week_start:
                                add_to_stats(category, day_seconds, "week")
                            
                            # 本月
                            if current_day_start >= month_start:
                                add_to_stats(category, day_seconds, "month")
                            
                            # 本年
                            if current_day_start >= year_start:
                                add_to_stats(category, day_seconds, "year")
                        
                        current_day_start = next_day_start
                    
                    # 总计（不分摊，直接加）
                    add_to_stats(category, duration_seconds, "total")
                    
                except Exception as e:
                    print(f"⚠️ 解析记录时出错：{e}")
                    continue
    except Exception as e:
        print(f"⚠️ 读取CSV文件时出错：{e}")
    
    return stats

def check_unlock_phrase(text):
    """检查文本是否包含解锁短语"""
    text_lower = text.lower()
    for phrase in UNLOCK_PHRASES:
        if phrase in text_lower:
            return True
    return False

def unlock_monitor():
    """解锁监控并结束当前锁定任务，然后自动检测前台App切换任务"""
    monitor_lock_file = "/home/operit/monitor_lock.json"
    current_task_file = "/home/operit/current_task.json"
    time_log_file = "/home/operit/time_log.csv"
    web_status_file = "/data/user/0/com.ai.assistance.operit/files/workspace/ea9e1ec2-3f82-46e4-9c7a-a251ac5c747e/web_status.json"
    current_app_file = "/sdcard/OperitNotifications/current_app.txt"
    
    # 1. 先检查是否有正在运行的锁定任务
    ended_task = None
    if os.path.exists(current_task_file):
        try:
            with open(current_task_file, 'r', encoding='utf-8') as f:
                current_task = json.load(f)
            
            # 如果是锁定任务（吃饭/睡觉），需要结束它
            if current_task.get('running', False) and current_task.get('locked', False):
                start_time = datetime.fromisoformat(current_task['start_time'])
                end_time = get_current_time()
                duration_seconds = int((end_time - start_time).total_seconds())
                
                # 格式化时长
                hours, remainder = divmod(duration_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                formatted_duration = f"{hours}:{minutes:02d}:{seconds:02d}"
                
                # 获取备注
                prev_note = current_task.get('note', '')
                
                # 记录到CSV
                log_entry = f"{current_task['task_name']},{current_task['start_time']},{end_time.isoformat()},{duration_seconds},{formatted_duration},{prev_note}\n"
                with open(time_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
                
                ended_task = {
                    'name': current_task['task_name'],
                    'duration': duration_seconds,
                    'duration_str': formatted_duration
                }
                
                # 删除当前任务文件
                os.remove(current_task_file)
                print(f"✅ 已结束锁定任务：{current_task['task_name']}，用时：{duration_seconds//3600}小时{(duration_seconds%3600)//60}分钟")
        except Exception as e:
            print(f"⚠️ 结束锁定任务时出错：{e}")
    
    # 2. 写入解锁状态
    with open(monitor_lock_file, 'w', encoding='utf-8') as f:
        json.dump({
            "locked": False,
            "task_name": "",
            "lock_time": "",
            "reason": ""
        }, f, ensure_ascii=False, indent=2)
    
    # 3. 自动检测前台App并切换任务
    detected_package = None
    detected_category = None
    try:
        # 读取当前前台App（由Android端监控写入）
        if os.path.exists(current_app_file):
            with open(current_app_file, 'r') as f:
                content = f.read().strip()
                # 格式可能是 "包名" 或 "包名 类别名"
                detected_package = content.split()[0] if content else None
        
        if detected_package:
            print(f"📱 检测到前台App：{detected_package}")
            # 调用app_detect.py检测并切换任务
            result = subprocess.run(
                ['python3', '/home/operit/app_detect.py', 'detect', detected_package],
                capture_output=True, text=True, timeout=30
            )
            print(result.stdout)
            if result.returncode == 0:
                print("✅ 已自动切换到对应任务")
                return ended_task  # app_detect.py已经更新了状态，直接返回
        else:
            print("⚠️ 无法获取前台App信息")
    except Exception as e:
        print(f"⚠️ 自动检测前台App时出错：{e}")
    
    # 4. 如果自动检测失败，更新Web状态为空闲（兜底）
    try:
        web_status = {
            "task_name": "空闲",
            "action": "stop",
            "timestamp": get_current_time().isoformat(),
            "running": False,
            "elapsed_seconds": 0,
            "stats": calculate_statistics()
        }
        with open(web_status_file, 'w', encoding='utf-8') as f:
            json.dump(web_status, f, ensure_ascii=False, indent=2)
        print("✅ Web状态已更新：空闲（自动检测失败）")
    except Exception as e:
        print(f"⚠️ 更新Web状态时出错：{e}")
    
    return ended_task

def format_duration(seconds):
    """格式化时间为小时和分钟"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"

def main():
    if len(sys.argv) < 2:
        print("❌ 请提供任务名称")
        print("使用方法：python3 start_task.py <任务名> [备注]")
        print("示例：python3 start_task.py 洗漱 洗澡")
        sys.exit(1)
    
    task_name = sys.argv[1]
    note = sys.argv[2] if len(sys.argv) > 2 else ""  # 获取备注参数
    
    # 检查是否是解锁短语（吃完了、睡醒了等）
    if check_unlock_phrase(task_name):
        print(f"🔓 检测到解锁短语：{task_name}")
        ended_task = unlock_monitor()
        if ended_task:
            print(f"🌅 {ended_task['name']}结束，共{ended_task['duration']//3600}小时{(ended_task['duration']%3600)//60}分钟")
        print("✅ 监控已解锁，自动监控恢复正常")
        sys.exit(0)
    
    print(f"🚀 开始执行任务：{task_name}" + (f"（备注：{note}）" if note else ""))
    
    # 数据文件路径
    current_task_file = "/home/operit/current_task.json"
    time_log_file = "/home/operit/time_log.csv"
    web_status_file = "/data/user/0/com.ai.assistance.operit/files/workspace/ea9e1ec2-3f82-46e4-9c7a-a251ac5c747e/web_status.json"
    
    # 1. 停止当前任务（如果有）
    if os.path.exists(current_task_file):
        try:
            with open(current_task_file, 'r', encoding='utf-8') as f:
                current_task = json.load(f)
            
            if current_task.get('running', False):
                # 计算持续时间
                start_time = datetime.fromisoformat(current_task['start_time'])
                end_time = get_current_time()
                duration_seconds = int((end_time - start_time).total_seconds())
                
                # 格式化时长
                hours, remainder = divmod(duration_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                formatted_duration = f"{hours}:{minutes:02d}:{seconds:02d}"
                
                # 获取上一条记录的备注（如果有）
                prev_note = current_task.get('note', '')
                
                # 记录到CSV（包含备注列）
                log_entry = f"{current_task['task_name']},{current_task['start_time']},{end_time.isoformat()},{duration_seconds},{formatted_duration},{prev_note}\n"
                with open(time_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
                
                print(f"✅ 已停止：{current_task['task_name']}，用时：{duration_seconds}秒")
        except Exception as e:
            print(f"⚠️ 停止任务时出错：{e}")
    
    # 2. 开始新任务
    now_local = get_current_time()
    
    # 检查是否需要锁定监控
    is_locked = task_name in LOCKED_TASKS
    
    new_task = {
        "task_name": task_name,
        "start_time": now_local.isoformat(),
        "running": True,
        "note": note,  # 保存备注到当前任务
        "locked": is_locked  # 锁定状态：吃饭/睡觉时暂停自动监控
    }
    
    # 写入监控锁定状态文件（供 app_monitor_v2.py 读取）
    monitor_lock_file = "/home/operit/monitor_lock.json"
    with open(monitor_lock_file, 'w', encoding='utf-8') as f:
        json.dump({
            "locked": is_locked,
            "task_name": task_name,
            "lock_time": now_local.isoformat(),
            "reason": f"用户切换到锁定任务: {task_name}" if is_locked else ""
        }, f, ensure_ascii=False, indent=2)
    
    with open(current_task_file, 'w', encoding='utf-8') as f:
        json.dump(new_task, f, ensure_ascii=False, indent=2)
    
    if is_locked:
        print(f"🔒 监控已锁定：{task_name}（自动监控暂停，说'吃完了/睡醒了'解锁）")
    
    print(f"✅ 已开始记录：{task_name}，开始时间：{now_local.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 发送通知
    send_notification("🔄 任务切换", f"已切换到: {task_name}")
    
    # 3. 读取CSV数据算出统计数据
    print("📊 计算统计数据...")
    stats = calculate_statistics()
    
    # 4. 创建Web状态（包含统计数据）
    web_status = {
        "task_name": task_name,
        "action": "start",
        "timestamp": now_local.isoformat(),
        "running": True,
        "elapsed_seconds": 0,
        "note": note,  # 包含备注
        "stats": stats
    }
    
    # 5. 写入Web状态文件（喂给Web界面）
    with open(web_status_file, 'w', encoding='utf-8') as f:
        json.dump(web_status, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Web状态已更新：{task_name} - 运行中")
    print(f"📊 统计数据已计算并喂给Web界面")
    
    # 显示今日统计摘要
    today_stats = stats["today"]
    if today_stats["total_seconds"] > 0:
        print(f"📈 今日总计：{format_duration(today_stats['total_seconds'])}")
        for category, seconds in sorted(today_stats["categories"].items(), key=lambda x: x[1], reverse=True):
            percentage = (seconds / today_stats["total_seconds"]) * 100
            print(f"   {category}: {format_duration(seconds)} ({percentage:.1f}%)")
    
    print(f"🎉 任务'{task_name}'执行完成！")
    print("📱 Web页面已更新，请刷新查看")

if __name__ == "__main__":
    main()