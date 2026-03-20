#!/usr/bin/env python3
"""App自动监控服务 V3 - 从Android端读取前台App信息

工作原理：
  - Android端脚本(monitor_android.sh)每10秒检测前台App并写入文件
  - 本脚本读取/sdcard/OperitNotifications/current_app.txt获取信息
  - 支持熄屏检测（SCREEN_OFF）

使用方法：
  python3 app_monitor_v2.py start    # 启动后台监控
  python3 app_monitor_v2.py stop     # 停止监控
  python3 app_monitor_v2.py status   # 查看监控状态
"""
import sys
import os
import json
import time
import subprocess
from datetime import datetime
import signal

BASE_DIR = "/home/operit"
APP_DETECT_SCRIPT = os.path.join(BASE_DIR, "app_detect.py")
MONITOR_PID_FILE = os.path.join(BASE_DIR, "app_monitor_v2.pid")
MONITOR_LOG_FILE = os.path.join(BASE_DIR, "app_monitor_v2.log")
MONITOR_CONFIG_FILE = os.path.join(BASE_DIR, "app_monitor_config.json")
MONITOR_LOCK_FILE = os.path.join(BASE_DIR, "monitor_lock.json")  # 监控锁定文件
APP_INFO_FILE = "/sdcard/OperitNotifications/current_app.txt"

DEFAULT_CONFIG = {
    "interval": 10,
    "enabled": True,
    "ignore_packages": [
        "com.ai.assistance.operit",
        "com.android.launcher",
        "com.miui.home",
        "com.android.systemui",
    ],
    "min_switch_interval": 30,
    "log_enabled": True,
}

def is_monitor_locked():
    """检查监控是否被锁定（吃饭/睡觉时暂停自动切换）"""
    if os.path.exists(MONITOR_LOCK_FILE):
        try:
            with open(MONITOR_LOCK_FILE, 'r', encoding='utf-8') as f:
                lock_data = json.load(f)
            return lock_data.get('locked', False)
        except:
            pass
    return False

def get_lock_info():
    """获取锁定信息"""
    if os.path.exists(MONITOR_LOCK_FILE):
        try:
            with open(MONITOR_LOCK_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"locked": False, "task_name": "", "reason": ""}

def load_config():
    if os.path.exists(MONITOR_CONFIG_FILE):
        try:
            with open(MONITOR_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except:
            pass
    return DEFAULT_CONFIG.copy()

def log(message):
    config = load_config()
    if not config.get("log_enabled", True):
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    try:
        with open(MONITOR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except:
        pass
    print(log_line.strip())

def get_front_app():
    """从Android端写入的文件获取前台App"""
    try:
        if os.path.exists(APP_INFO_FILE):
            with open(APP_INFO_FILE, 'r') as f:
                package = f.read().strip()
            if package:
                return package
        return None
    except Exception as e:
        log(f"⚠️ 读取App文件失败: {e}")
        return None

def check_and_switch(package_name, config, last_switch_time):
    """检测并切换任务"""
    if not package_name:
        return last_switch_time
    
    # 忽略列表
    if package_name in config.get("ignore_packages", []):
        return last_switch_time
    
    # 最小切换间隔
    now = time.time()
    min_interval = config.get("min_switch_interval", 30)
    if now - last_switch_time < min_interval:
        return last_switch_time
    
    try:
        # 判断是熄屏/锁屏还是正常App
        if package_name == "SCREEN_OFF" or package_name == "SCREEN_LOCKED":
            # 熄屏或锁屏：直接传入信号让detect_with_screen处理
            result = subprocess.run(
                ['python3', APP_DETECT_SCRIPT, 'detect', package_name],
                capture_output=True, text=True, timeout=10
            )
        else:
            result = subprocess.run(
                ['python3', APP_DETECT_SCRIPT, 'detect', package_name],
                capture_output=True, text=True, timeout=10
            )
        
        output = result.stdout.strip()
        if "已自动切换" in output or "已切换" in output:
            log(f"✅ 切换成功: {output}")
            return now
        elif "未切换" not in output:
            log(f"检测结果: {output}")
    except Exception as e:
        log(f"检测失败: {e}")
    
    return last_switch_time

def run_monitor():
    """运行监控主循环"""
    config = load_config()
    interval = config.get("interval", 10)
    
    with open(MONITOR_PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    log(f"🚀 自动监控服务V3启动，检测间隔: {interval}秒")
    log(f"   读取App信息: {APP_INFO_FILE}")
    
    last_package = None
    last_switch_time = 0
    no_change_count = 0
    lock_logged = False  # 是否已记录锁定状态
    
    while True:
        try:
            config = load_config()
            interval = config.get("interval", 10)
            
            if not config.get("enabled", True):
                log("⏸️ 监控已禁用，等待...")
                time.sleep(interval)
                continue
            
            # 检查监控是否被锁定（吃饭/睡觉时不自动切换）
            if is_monitor_locked():
                lock_info = get_lock_info()
                if not lock_logged:
                    log(f"🔒 监控已锁定: {lock_info.get('task_name', '未知')} - {lock_info.get('reason', '')}")
                    lock_logged = True
                time.sleep(interval)
                continue
            else:
                if lock_logged:
                    log("🔓 监控已解锁，恢复正常检测")
                    lock_logged = False
            
            package = get_front_app()
            
            if package:
                # 检测到有效信息
                if package == "SCREEN_OFF" or package == "SCREEN_LOCKED":
                    # 熄屏或锁屏状态
                    screen_state = "熄屏" if package == "SCREEN_OFF" else "锁屏"
                    if last_package != package:
                        log(f"📺 屏幕状态变化: {last_package or '未知'} → {screen_state}")
                        last_switch_time = check_and_switch(package, config, last_switch_time)
                        last_package = package
                        no_change_count = 0
                    else:
                        no_change_count += 1
                        if no_change_count % 20 == 0:
                            log(f"📺 状态稳定: {screen_state}")
                else:
                    # 正常App
                    if package != last_package:
                        log(f"📱 App变化: {last_package or '无'} → {package}")
                        last_switch_time = check_and_switch(package, config, last_switch_time)
                        last_package = package
                        no_change_count = 0
                    else:
                        no_change_count += 1
                        if no_change_count % 20 == 0:
                            log(f"📍 状态稳定: {package}")
            else:
                # 无法获取信息
                if last_package != "unknown":
                    log("⚠️ 无法获取前台App信息（Android监控可能未运行）")
                    last_package = "unknown"
            
            time.sleep(interval)
            
        except KeyboardInterrupt:
            log("收到停止信号")
            break
        except Exception as e:
            log(f"监控异常: {e}")
            time.sleep(interval)
    
    if os.path.exists(MONITOR_PID_FILE):
        os.remove(MONITOR_PID_FILE)
    log("监控服务已停止")

def is_process_running(pid):
    """检查进程是否运行（兼容Proot环境）"""
    try:
        # 使用 /proc 检查进程状态
        return os.path.exists(f"/proc/{pid}")
    except:
        return False

def start_monitor():
    """启动监控服务"""
    if os.path.exists(MONITOR_PID_FILE):
        try:
            with open(MONITOR_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            if is_process_running(pid):
                print(f"⚠️ 监控服务V3已在运行 (PID: {pid})")
                return
            else:
                os.remove(MONITOR_PID_FILE)
        except (ValueError, FileNotFoundError):
            pass
    
    print("🚀 启动App自动监控服务V3...")
    subprocess.Popen(
        ['nohup', 'python3', __file__, '_run'],
        stdout=open(MONITOR_LOG_FILE, 'a'),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    time.sleep(1)
    
    if os.path.exists(MONITOR_PID_FILE):
        with open(MONITOR_PID_FILE, 'r') as f:
            pid = f.read().strip()
        print(f"✅ 监控服务V3已启动 (PID: {pid})")
        print(f"   检测间隔: {load_config().get('interval', 10)}秒")
        print(f"   日志文件: {MONITOR_LOG_FILE}")
    else:
        print("⚠️ 启动可能失败，请检查日志")

def stop_monitor():
    """停止监控服务"""
    if not os.path.exists(MONITOR_PID_FILE):
        print("⚠️ 监控服务V3未运行")
        return
    
    try:
        with open(MONITOR_PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # 使用 kill 命令发送信号
        subprocess.run(['kill', str(pid)], capture_output=True)
        print(f"✅ 已发送停止信号 (PID: {pid})")
        
        for _ in range(5):
            if not is_process_running(pid):
                break
            time.sleep(0.5)
        
        if os.path.exists(MONITOR_PID_FILE):
            os.remove(MONITOR_PID_FILE)
        print("✅ 监控服务V3已停止")
    except Exception as e:
        print(f"❌ 停止失败: {e}")
        if os.path.exists(MONITOR_PID_FILE):
            os.remove(MONITOR_PID_FILE)

def show_status():
    """显示监控状态"""
    config = load_config()
    
    print("📊 App自动监控服务V3状态")
    print("=" * 40)
    
    if os.path.exists(MONITOR_PID_FILE):
        try:
            with open(MONITOR_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            if is_process_running(pid):
                print(f"Proot端状态: ✅ 运行中 (PID: {pid})")
            else:
                print("Proot端状态: ❌ 已停止（PID文件存在但进程不存在）")
        except (ValueError, FileNotFoundError):
            print("Proot端状态: ❌ PID文件损坏")
    else:
        print("Proot端状态: ❌ 未运行")
    
    # 检查Android端监控
    print("\nAndroid端监控状态:")
    if os.path.exists(APP_INFO_FILE):
        package = open(APP_INFO_FILE).read().strip()
        mtime = datetime.fromtimestamp(os.path.getmtime(APP_INFO_FILE))
        if package == "SCREEN_OFF" or package == "SCREEN_LOCKED":
            print(f"  当前状态: 📺 {"熄屏" if package == "SCREEN_OFF" else "锁屏"}")
        else:
            print(f"  当前App: {package}")
        print(f"  信息更新: {mtime.strftime('%H:%M:%S')}")
        
        # 检查Android监控进程
        if os.path.exists("/sdcard/monitor_android.pid"):
            android_pid = open("/sdcard/monitor_android.pid").read().strip()
            print(f"  Android监控PID: {android_pid}")
    else:
        print("  ⚠️ App信息文件不存在")
    
    print(f"\n配置:")
    print(f"  检测间隔: {config.get('interval', 10)}秒")
    print(f"  最小切换间隔: {config.get('min_switch_interval', 30)}秒")
    print(f"  是否启用: {'是' if config.get('enabled', True) else '否'}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n当前配置:")
        show_status()
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == 'start':
        start_monitor()
    elif command == 'stop':
        stop_monitor()
    elif command == 'status':
        show_status()
    elif command == '_run':
        run_monitor()
    elif command == 'set' and len(sys.argv) >= 4:
        config = load_config()
        key, value = sys.argv[2], sys.argv[3]
        if key == 'interval':
            config['interval'] = int(value)
        elif key == 'min_switch_interval':
            config['min_switch_interval'] = int(value)
        elif key == 'enabled':
            config['enabled'] = value.lower() in ['true', '1', 'yes']
        with open(MONITOR_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"✅ 已更新: {key} = {value}")
    else:
        print(__doc__)
