#!/usr/bin/env python3
"""
监控看门狗 v3.2 - Android脚本监控版
改进：
  1. 心跳文件检测 - 防止"僵尸"状态（进程存在但不工作）
  2. 双重检查 - 进程存在 + 日志更新
  3. 自动清理僵尸进程
  4. 详细的恢复日志
  5. 支持持续运行模式（_run参数）
  6. v3.1: 监控Operit工作流心跳（App自动检测工作流每30秒写入心跳）
  7. v3.2: 添加Android监控脚本监控（熄屏检测的核心数据源）
检查项：
  1. cron服务（定时任务基础）
  2. Proot监控进程 + 心跳检测
  3. API服务器
  4. Operit工作流心跳（workflow_heartbeat.txt）+ current_app.txt更新
  5. Prime智能系统
  6. Android监控脚本（熄屏检测核心）- v3.2新增
架构说明：
  - Android脚本（monitor_app.sh）检测熄屏状态，写入SCREEN_OFF
  - 工作流每30秒执行一次，写入心跳文件
  - Proot监控读取current_app.txt进行任务切换
"""
import os
import sys
import subprocess
import time
import fcntl
import signal
from datetime import datetime

BASE_DIR = "/home/operit"
LOCK_FILE = os.path.join(BASE_DIR, "watchdog.lock")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "watchdog_heartbeat.txt")
OWN_PID_FILE = os.path.join(BASE_DIR, "watchdog.pid")
MONITOR_SCRIPT = os.path.join(BASE_DIR, "app_monitor_v2.py")
API_SCRIPT = os.path.join(BASE_DIR, "api_server.py")
APP_LOG_FILE = os.path.join(BASE_DIR, "app_monitor_v2.log")
WATCHDOG_LOG = os.path.join(BASE_DIR, "watchdog.log")
ANDROID_APP_FILE = "/sdcard/OperitNotifications/current_app.txt"
WORKFLOW_HEARTBEAT_FILE = "/sdcard/OperitNotifications/workflow_heartbeat.txt"

# Android监控脚本配置 - v3.2新增
ANDROID_MONITOR_DIR = "/sdcard/OperitNotifications"
ANDROID_MONITOR_SCRIPT = os.path.join(ANDROID_MONITOR_DIR, "monitor_app.sh")
ANDROID_MONITOR_LOG = os.path.join(ANDROID_MONITOR_DIR, "monitor_app.log")
ANDROID_MONITOR_HEARTBEAT = os.path.join(ANDROID_MONITOR_DIR, "monitor_heartbeat.txt")
ANDROID_MONITOR_PID = os.path.join(ANDROID_MONITOR_DIR, "monitor.pid")

# Prime系统配置
PRIME_DIR = os.path.join(BASE_DIR, "prime")
PRIME_WATCHDOG = os.path.join(PRIME_DIR, "prime_watchdog.py")

# 阈值配置
MAX_LOG_SILENCE = 120  # 日志最大静默时间（秒）
MAX_WORKFLOW_SILENCE = 90  # 工作流心跳最大静默时间（秒）- 工作流30秒执行一次
MAX_ANDROID_SILENCE = 300  # Android监控最大静默时间（秒）
MAX_ANDROID_MONITOR_SILENCE = 180  # Android脚本心跳最大静默时间（秒）- 脚本10秒更新一次
HEARTBEAT_INTERVAL = 30  # 心跳写入间隔（秒）


def log(message):
    """写入日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(WATCHDOG_LOG, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')


def update_heartbeat():
    """更新心跳文件"""
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(str(int(time.time())))
    except:
        pass


def get_heartbeat_age(filepath):
    """获取心跳文件的年龄（秒）"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return time.time() - int(f.read().strip())
        return float('inf')
    except:
        return float('inf')


def check_cron():
    """检查cron服务是否运行"""
    try:
        result = subprocess.run(
            "pgrep -x cron || pgrep -x crond",
            shell=True, capture_output=True, text=True
        )
        if result.stdout.strip():
            return True, "运行中"
        
        # 尝试启动cron
        log("⚠️ cron服务未运行，尝试启动...")
        subprocess.run("service cron start 2>/dev/null || service crond start 2>/dev/null", 
                       shell=True, capture_output=True)
        time.sleep(1)
        
        # 再次检查
        result = subprocess.run(
            "pgrep -x cron || pgrep -x crond",
            shell=True, capture_output=True, text=True
        )
        if result.stdout.strip():
            log("✅ cron服务已启动")
            return True, "已启动"
        else:
            log("❌ cron服务启动失败")
            return False, "启动失败"
    except Exception as e:
        log(f"❌ 检查cron失败: {e}")
        return False, str(e)


def check_process(name, pattern):
    """检查进程是否存在"""
    try:
        result = subprocess.run(
            f"ps aux | grep '{pattern}' | grep -v grep",
            shell=True, capture_output=True, text=True
        )
        return bool(result.stdout.strip())
    except:
        return False


def get_pids(pattern):
    """获取进程PID列表"""
    try:
        result = subprocess.run(
            f"ps aux | grep '{pattern}' | grep -v grep | awk '{{print $2}}'",
            shell=True, capture_output=True, text=True
        )
        return [int(p) for p in result.stdout.strip().split('\n') if p.strip()]
    except:
        return []


def kill_process(pattern):
    """终止进程"""
    pids = get_pids(pattern)
    for pid in pids:
        try:
            subprocess.run(['kill', '-9', str(pid)], capture_output=True)
            log(f"🔪 已终止进程 PID={pid}")
        except Exception as e:
            log(f"❌ 终止进程失败: {e}")
    time.sleep(1)


def start_monitor():
    """启动Proot监控"""
    try:
        subprocess.run(
            f'nohup python3 {MONITOR_SCRIPT} _run >> {APP_LOG_FILE} 2>&1 &',
            shell=True, capture_output=True
        )
        time.sleep(2)
        if check_process("monitor", "app_monitor_v2.py _run"):
            log("✅ Proot监控已启动")
            return True
        log("❌ Proot监控启动失败")
        return False
    except Exception as e:
        log(f"❌ 启动监控失败: {e}")
        return False


def start_api():
    """启动API服务器"""
    try:
        subprocess.run(
            f'nohup python3 {API_SCRIPT} > /tmp/api_server.log 2>&1 &',
            shell=True, capture_output=True
        )
        time.sleep(2)
        if check_process("api", "api_server.py"):
            log("✅ API服务器已启动")
            return True
        log("❌ API服务器启动失败")
        return False
    except Exception as e:
        log(f"❌ 启动API失败: {e}")
        return False


def check_prime_services():
    """检查Prime系统所有服务状态"""
    try:
        result = subprocess.run(
            ['python3', PRIME_WATCHDOG, '--status'],
            capture_output=True, text=True, timeout=30
        )
        return True, result.stdout
    except Exception as e:
        return False, str(e)


def start_prime_system():
    """启动Prime智能系统"""
    try:
        # 检查Prime看门狗是否运行
        if check_process("prime_watchdog", "prime_watchdog.py --run"):
            log("✅ Prime看门狗已运行")
        else:
            # 启动Prime看门狗（它会自动管理所有服务）
            subprocess.run(
                f'nohup python3 {PRIME_WATCHDOG} --run >> {PRIME_DIR}/logs/prime_watchdog.log 2>&1 &',
                shell=True, capture_output=True
            )
            time.sleep(3)
            if check_process("prime_watchdog", "prime_watchdog.py --run"):
                log("✅ Prime看门狗已启动")
            else:
                log("❌ Prime看门狗启动失败")
                return False
        return True
    except Exception as e:
        log(f"❌ 启动Prime系统失败: {e}")
        return False


def check_android_monitor():
    """
    检查Android监控脚本状态 - v3.2新增
    这是熄屏检测的核心数据源，必须确保运行
    """
    try:
        # 检查心跳文件
        if os.path.exists(ANDROID_MONITOR_HEARTBEAT):
            age = get_heartbeat_age(ANDROID_MONITOR_HEARTBEAT)
            if age < MAX_ANDROID_MONITOR_SILENCE:
                return True, f"运行中({int(age)}秒前更新)"
            else:
                log(f"⚠️ Android脚本心跳超时: {int(age)}秒")
                return False, f"心跳超时({int(age)}秒)"
        
        # 没有心跳文件，检查日志
        if os.path.exists(ANDROID_MONITOR_LOG):
            mtime = os.path.getmtime(ANDROID_MONITOR_LOG)
            age = time.time() - mtime
            if age > MAX_ANDROID_MONITOR_SILENCE:
                return False, f"日志{int(age)}秒未更新"
        
        return False, "未运行"
    except Exception as e:
        return False, str(e)


def start_android_monitor():
    """
    启动Android监控脚本 - v3.2新增
    使用Shizuku权限在Android端启动
    """
    try:
        log("🔄 尝试启动Android监控脚本...")
        
        # 方法1: 使用Shizuku执行shell脚本
        result = subprocess.run(
            f'su -c "cd {ANDROID_MONITOR_DIR} && sh monitor_app.sh &"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        
        time.sleep(2)
        
        # 验证是否启动成功
        ok, msg = check_android_monitor()
        if ok:
            log(f"✅ Android监控脚本已启动: {msg}")
            return True
        
        # 方法2: 直接通过Shizuku启动
        log("⚠️ 方法1失败，尝试方法2...")
        result = subprocess.run(
            f'su -c "nohup sh {ANDROID_MONITOR_SCRIPT} > /dev/null 2>&1 &"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        
        time.sleep(2)
        ok, msg = check_android_monitor()
        if ok:
            log(f"✅ Android监控脚本已启动: {msg}")
            return True
        
        log("❌ Android监控脚本启动失败")
        return False
    except Exception as e:
        log(f"❌ 启动Android脚本失败: {e}")
        return False


def check_workflow_heartbeat():
    """检查Operit工作流心跳（App自动检测工作流）"""
    try:
        # 优先检查工作流心跳文件
        if os.path.exists(WORKFLOW_HEARTBEAT_FILE):
            age = get_heartbeat_age(WORKFLOW_HEARTBEAT_FILE)
            if age < MAX_WORKFLOW_SILENCE:
                return True, f"心跳正常({int(age)}秒前)"
            else:
                log(f"⚠️ 工作流心跳超时: {int(age)}秒")
                # 回退检查current_app.txt
                if os.path.exists(ANDROID_APP_FILE):
                    app_age = time.time() - os.path.getmtime(ANDROID_APP_FILE)
                    if app_age < MAX_ANDROID_SILENCE:
                        return True, f"心跳超时但App文件正常({int(app_age)}秒前)"
                return False, f"心跳超时({int(age)}秒)"
        
        # 没有心跳文件，检查current_app.txt
        if not os.path.exists(ANDROID_APP_FILE):
            log("⚠️ current_app.txt 不存在")
            return False, "文件不存在"
        
        mtime = os.path.getmtime(ANDROID_APP_FILE)
        age = time.time() - mtime
        
        if age > MAX_ANDROID_SILENCE:
            return False, f"{int(age)}秒未更新"
        return True, f"正常({int(age)}秒前更新)"
    except Exception as e:
        return False, str(e)


def check_log_update():
    """检查日志文件是否在更新"""
    try:
        if not os.path.exists(APP_LOG_FILE):
            return False, "日志文件不存在"
        
        mtime = os.path.getmtime(APP_LOG_FILE)
        age = time.time() - mtime
        
        if age > MAX_LOG_SILENCE:
            return False, f"{int(age)}秒未更新"
        return True, f"{int(age)}秒前更新"
    except Exception as e:
        return False, str(e)


def check_once():
    """单次检查所有服务"""
    log("🐕 看门狗检查...")
    update_heartbeat()  # 写入心跳
    issues = []
    
    # 1. 检查cron服务
    cron_ok, cron_msg = check_cron()
    if not cron_ok:
        issues.append(f"cron: {cron_msg}")
    else:
        log(f"✅ cron服务: {cron_msg}")
    
    # 2. 检查Proot监控进程（双重检查）
    monitor_running = check_process("monitor", "app_monitor_v2.py _run")
    log_ok, log_msg = check_log_update()
    
    if monitor_running and log_ok:
        pids = get_pids("app_monitor_v2.py _run")
        log(f"✅ Proot监控运行中 (PID: {pids}, {log_msg})")
    elif monitor_running and not log_ok:
        # 进程存在但日志不更新 = 僵尸状态
        log(f"⚠️ Proot监控僵尸状态: {log_msg}")
        issues.append(f"监控僵尸: {log_msg}")
        kill_process("app_monitor_v2.py _run")
        if start_monitor():
            log("🎉 监控已重启")
    else:
        log("⚠️ Proot监控未运行")
        issues.append("Proot监控未运行")
        if start_monitor():
            log("🎉 监控已启动")
    
    # 3. 检查API服务器
    if check_process("api", "api_server.py"):
        log("✅ API服务器运行中")
    else:
        log("⚠️ API服务器未运行")
        issues.append("API未运行")
        if start_api():
            log("🎉 API已启动")
    
    # 4. 检查Android监控脚本 - v3.2新增
    android_ok, android_msg = check_android_monitor()
    if android_ok:
        log(f"✅ Android监控: {android_msg}")
    else:
        log(f"⚠️ Android监控: {android_msg}")
        issues.append(f"Android脚本: {android_msg}")
        if start_android_monitor():
            log("🎉 Android监控已启动")
    
    # 5. 检查Operit工作流心跳
    workflow_ok, workflow_msg = check_workflow_heartbeat()
    if workflow_ok:
        log(f"✅ 工作流心跳: {workflow_msg}")
    else:
        log(f"⚠️ 工作流心跳: {workflow_msg}")
        issues.append(f"工作流: {workflow_msg}")
        # 工作流无法从这里重启，只能记录警告
    
    # 6. 检查Prime智能系统
    if check_process("prime_watchdog", "prime_watchdog.py --run"):
        pids = get_pids("prime_watchdog.py --run")
        log(f"✅ Prime看门狗运行中 (PID: {pids})")
        
        # 检查Prime各服务状态
        prime_ok, prime_status = check_prime_services()
        if prime_ok:
            if "❌" in prime_status or "已停止" in prime_status:
                log(f"⚠️ Prime服务状态异常")
                issues.append("Prime服务异常")
            else:
                log(f"✅ Prime服务正常")
        else:
            log(f"⚠️ 无法获取Prime服务状态: {prime_status}")
    else:
        log("⚠️ Prime看门狗未运行")
        issues.append("Prime看门狗未运行")
        if start_prime_system():
            log("🎉 Prime系统已启动")
    
    if issues:
        log(f"⚠️ 发现问题: {', '.join(issues)}")
        return False
    else:
        log("✅ 所有服务正常")
        return True


def run_continuous():
    """持续运行模式（带心跳）"""
    log("🐕 看门狗启动，持续监控模式")
    
    # 写入自己的PID
    try:
        with open(OWN_PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except:
        pass
    
    while True:
        try:
            check_once()
        except Exception as e:
            log(f"❌ 检查出错: {e}")
        time.sleep(60)


def acquire_lock():
    """获取锁，防止重复运行"""
    try:
        lock_file = open(LOCK_FILE, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except (IOError, BlockingIOError):
        # 另一个实例正在运行
        return None


def main():
    # 单次检查模式使用锁防止重复运行
    if len(sys.argv) <= 1 or sys.argv[1] != '_run':
        lock = acquire_lock()
        if lock is None:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ 看门狗已在运行，跳过")
            sys.exit(0)
        try:
            check_once()
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()
    else:
        run_continuous()


if __name__ == "__main__":
    main()
