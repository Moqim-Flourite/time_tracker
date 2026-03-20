#!/usr/bin/env python3
"""
通知发送脚本 - 读取通知队列并发送Android通知
运行环境：Android shell（需要Shizuku权限）
使用方法：python3 send_notifications.py

注意：此脚本通过 super_admin:shell 在Android环境中运行，
可以直接使用 os.system 调用 cmd notification 命令
"""

import os
import json
from datetime import datetime

BASE_DIR = "/home/operit"
NOTIFICATION_QUEUE = os.path.join(BASE_DIR, "notification_queue.json")
SENT_LOG = os.path.join(BASE_DIR, "notification_sent.log")


def send_notification_android(title, content):
    """通过cmd notification发送通知"""
    try:
        # 转义引号防止命令注入
        title_escaped = title.replace('"', '\\"').replace("'", "\\'")
        content_escaped = content.replace('"', '\\"').replace("'", "\\'")
        
        # 直接使用os.system执行shell命令（在Android shell环境中）
        cmd = f'cmd notification post -t "{title_escaped}" app_monitor "{content_escaped}"'
        result = os.system(cmd)
        return result == 0
    except Exception as e:
        print(f"发送失败: {e}")
        return False


def main():
    if not os.path.exists(NOTIFICATION_QUEUE):
        return
    
    try:
        with open(NOTIFICATION_QUEUE, 'r', encoding='utf-8') as f:
            queue = json.load(f)
    except Exception as e:
        print(f"读取队列失败: {e}")
        queue = []
    
    if not queue:
        return
    
    # 发送所有待发送的通知（只发送最后一条）
    # 因为通知ID相同，只会显示最后一条
    last_notification = queue[-1]
    title = last_notification.get('title', '通知')
    content = last_notification.get('content', '')
    
    if send_notification_android(title, content):
        print(f"✅ 已发送: {title} - {content}")
        # 记录发送日志
        try:
            with open(SENT_LOG, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().isoformat()}] 发送: {title} - {content}\n")
        except:
            pass
    
    # 清空队列
    try:
        with open(NOTIFICATION_QUEUE, 'w', encoding='utf-8') as f:
            json.dump([], f)
    except Exception as e:
        print(f"清空队列失败: {e}")


if __name__ == "__main__":
    main()