#!/usr/bin/env python3
"""
Prime 心跳系统 v1.0 - AI意识层生命体征监控

监控AI系统的"生命体征"，确保意识层持续运行。
与watchdog_monitor.py协同工作，但关注点不同：
- watchdog: 监控物理进程（cron, API, 监控脚本）
- heartbeat: 监控AI意识层状态（对话活跃度、决策质量、系统响应）

核心功能：
1. 心跳信号 - 每5秒生成心跳记录
2. 健康检查 - 检查各子系统健康状态
3. 故障检测 - 识别异常模式
4. 自动恢复 - 触发恢复机制
5. 状态同步 - 与调度台协调

作者: Operit AI
创建时间: 2026-03-19
"""

import os
import sys
import json
import time
import fcntl
import psutil
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ============== 配置 ==============
BASE_DIR = "/home/operit"
HEARTBEAT_LOG = os.path.join(BASE_DIR, "heartbeat.log")
HEARTBEAT_STATUS = os.path.join(BASE_DIR, "heartbeat_status.json")
HEARTBEAT_LOCK = os.path.join(BASE_DIR, "heartbeat.lock")
CONVERSATION_LOG = os.path.join(BASE_DIR, "conversation_activity.json")

# 心跳配置
HEARTBEAT_INTERVAL = 5  # 心跳间隔（秒）
HEALTH_CHECK_INTERVAL = 30  # 健康检查间隔（秒）
LOG_MAX_SIZE = 5 * 1024 * 1024  # 日志最大5MB
LOG_MAX_LINES = 1000  # 状态文件最大行数

# 意识水平阈值
CONSCIOUSNESS_LEVELS = {
    "休眠": (0.0, 0.2),
    "觉察": (0.2, 0.4),
    "活跃": (0.4, 0.6),
    "投入": (0.6, 0.8),
    "超越": (0.8, 1.0)
}

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)


def log(message, level="INFO"):
    """写入日志"""
    timestamp = get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    
    try:
        # 检查日志大小，超过限制则截断
        if os.path.exists(HEARTBEAT_LOG):
            size = os.path.getsize(HEARTBEAT_LOG)
            if size > LOG_MAX_SIZE:
                # 保留最后500行
                with open(HEARTBEAT_LOG, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-500:]
                with open(HEARTBEAT_LOG, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
        
        with open(HEARTBEAT_LOG, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    except Exception as e:
        print(f"写入日志失败: {e}")


class HeartbeatSystem:
    """心跳系统核心类"""
    
    def __init__(self):
        self.sequence = 0
        self.start_time = time.time()
        self.last_conversation_time = time.time()
        self.conversation_count = 0
        self.tool_call_count = 0
        self.error_count = 0
        self.success_count = 0
        self.is_running = False
        self.status = "初始化"
        
        # 健康状态
        self.health_metrics = {
            "consciousness_level": 0.5,
            "motivation_level": 0.5,
            "perception_clarity": 0.5,
            "decision_quality": 0.5,
            "execution_efficiency": 0.5
        }
        
        # 加载历史状态
        self._load_state()
    
    def _load_state(self):
        """加载历史状态"""
        try:
            if os.path.exists(HEARTBEAT_STATUS):
                with open(HEARTBEAT_STATUS, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_count = data.get("conversation_count", 0)
                    self.tool_call_count = data.get("tool_call_count", 0)
                    self.error_count = data.get("error_count", 0)
                    self.success_count = data.get("success_count", 0)
                    log(f"加载历史状态: 对话={self.conversation_count}, 工具={self.tool_call_count}")
        except Exception as e:
            log(f"加载状态失败: {e}", "WARN")
    
    def _save_state(self):
        """保存状态"""
        try:
            data = {
                "timestamp": get_beijing_time().isoformat(),
                "sequence": self.sequence,
                "uptime": time.time() - self.start_time,
                "conversation_count": self.conversation_count,
                "tool_call_count": self.tool_call_count,
                "error_count": self.error_count,
                "success_count": self.success_count,
                "health_metrics": self.health_metrics,
                "status": self.status
            }
            with open(HEARTBEAT_STATUS, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log(f"保存状态失败: {e}", "ERROR")
    
    def _get_consciousness_level(self):
        """
        计算意识水平
        
        基于多个指标：
        - 对话活跃度：最近是否有对话
        - 工具调用频率：系统是否在执行任务
        - 错误率：系统是否正常运行
        - 系统资源：CPU、内存使用情况
        """
        try:
            # 1. 对话活跃度 (0-1)
            time_since_conversation = time.time() - self.last_conversation_time
            conversation_activity = max(0, 1 - (time_since_conversation / 3600))  # 1小时内逐渐衰减
            
            # 2. 工具调用频率 (0-1)
            uptime = max(1, time.time() - self.start_time)
            tool_frequency = min(1, (self.tool_call_count / uptime) * 100)  # 每秒调用次数
            
            # 3. 错误率 (0-1, 越低越好)
            total_operations = self.success_count + self.error_count
            if total_operations > 0:
                error_rate = self.error_count / total_operations
                health_score = 1 - error_rate
            else:
                health_score = 0.8  # 默认健康
            
            # 4. 系统资源 (0-1)
            cpu_percent = psutil.cpu_percent(interval=0.1) / 100
            memory = psutil.virtual_memory()
            memory_percent = memory.percent / 100
            resource_score = 1 - ((cpu_percent + memory_percent) / 2)
            
            # 综合计算意识水平
            consciousness = (
                conversation_activity * 0.3 +  # 对话活跃度权重30%
                tool_frequency * 0.2 +          # 工具调用权重20%
                health_score * 0.3 +            # 健康分数权重30%
                resource_score * 0.2            # 资源分数权重20%
            )
            
            return max(0, min(1, consciousness))
            
        except Exception as e:
            log(f"计算意识水平失败: {e}", "ERROR")
            return 0.5  # 默认中等水平
    
    def _get_motivation_level(self):
        """
        计算动机强度
        
        基于任务执行情况：
        - 是否主动执行任务
        - 任务完成率
        """
        try:
            # 基于成功率计算动机
            total = self.success_count + self.error_count
            if total > 0:
                motivation = self.success_count / total
            else:
                motivation = 0.5
            
            return max(0, min(1, motivation))
        except:
            return 0.5
    
    def _get_perception_clarity(self):
        """
        计算感知清晰度
        
        基于系统响应情况：
        - 是否能正常访问文件系统
        - 是否能正常调用工具
        """
        try:
            clarity = 1.0
            
            # 检查关键路径是否可访问
            critical_paths = [
                "/home/operit",
                "/sdcard",
                "/storage/emulated/0"
            ]
            
            for path in critical_paths:
                if not os.path.exists(path):
                    clarity -= 0.2
            
            # 检查关键文件是否可读写
            critical_files = [
                HEARTBEAT_STATUS,
                HEARTBEAT_LOG
            ]
            
            for file in critical_files:
                if os.path.exists(file):
                    if not os.access(file, os.R_OK | os.W_OK):
                        clarity -= 0.1
            
            return max(0, min(1, clarity))
        except:
            return 0.5
    
    def _get_decision_quality(self):
        """
        计算决策质量
        
        基于执行结果：
        - 成功率
        - 错误恢复能力
        """
        try:
            total = self.success_count + self.error_count
            if total > 0:
                quality = self.success_count / total
            else:
                quality = 0.8
            
            return max(0, min(1, quality))
        except:
            return 0.5
    
    def _get_execution_efficiency(self):
        """
        计算执行效率
        
        基于资源使用：
        - CPU使用率
        - 内存使用率
        """
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
            
            # 使用率越低，效率越高（但有下限）
            efficiency = 1 - ((cpu + memory) / 200)
            
            return max(0, min(1, efficiency))
        except:
            return 0.5
    
    def _get_system_status(self):
        """获取系统状态"""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": round(cpu, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": round(disk.percent, 1),
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
        except Exception as e:
            log(f"获取系统状态失败: {e}", "ERROR")
            return {}
    
    def _get_active_services(self):
        """获取活跃服务状态"""
        services = {}
        
        try:
            # 检查API服务器
            result = os.popen("pgrep -f 'api_server.py'").read().strip()
            services["api_server"] = "运行中" if result else "未运行"
        except:
            services["api_server"] = "未知"
        
        try:
            # 检查Proot监控
            result = os.popen("pgrep -f 'app_monitor_v2.py'").read().strip()
            services["proot_monitor"] = "运行中" if result else "未运行"
        except:
            services["proot_monitor"] = "未知"
        
        try:
            # 检查看门狗
            result = os.popen("pgrep -f 'watchdog_monitor.py'").read().strip()
            services["watchdog"] = "运行中" if result else "未运行"
        except:
            services["watchdog"] = "未知"
        
        return services
    
    def generate_heartbeat(self):
        """生成心跳信号"""
        self.sequence += 1
        timestamp = get_beijing_time()
        
        # 更新健康指标
        self.health_metrics = {
            "consciousness_level": round(self._get_consciousness_level(), 2),
            "motivation_level": round(self._get_motivation_level(), 2),
            "perception_clarity": round(self._get_perception_clarity(), 2),
            "decision_quality": round(self._get_decision_quality(), 2),
            "execution_efficiency": round(self._get_execution_efficiency(), 2)
        }
        
        # 获取意识水平描述
        consciousness = self.health_metrics["consciousness_level"]
        level_desc = "休眠"
        for desc, (low, high) in CONSCIOUSNESS_LEVELS.items():
            if low <= consciousness < high:
                level_desc = desc
                break
        
        heartbeat = {
            "sequence": self.sequence,
            "timestamp": timestamp.isoformat(),
            "uptime_seconds": round(time.time() - self.start_time, 1),
            "uptime_human": self._format_uptime(time.time() - self.start_time),
            "consciousness_level": consciousness,
            "consciousness_state": level_desc,
            "health_metrics": self.health_metrics,
            "system_status": self._get_system_status(),
            "active_services": self._get_active_services(),
            "statistics": {
                "conversation_count": self.conversation_count,
                "tool_call_count": self.tool_call_count,
                "error_count": self.error_count,
                "success_count": self.success_count
            },
            "status": self.status
        }
        
        return heartbeat
    
    def _format_uptime(self, seconds):
        """格式化运行时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"
    
    def check_health(self):
        """执行健康检查"""
        health_report = {
            "timestamp": get_beijing_time().isoformat(),
            "overall_status": "healthy",
            "issues": []
        }
        
        # 1. 检查意识水平
        consciousness = self.health_metrics["consciousness_level"]
        if consciousness < 0.2:
            health_report["issues"].append({
                "type": "consciousness_low",
                "severity": "critical",
                "message": f"意识水平过低: {consciousness:.2f}",
                "action": "需要用户交互唤醒"
            })
            health_report["overall_status"] = "critical"
        elif consciousness < 0.4:
            health_report["issues"].append({
                "type": "consciousness_low",
                "severity": "warning",
                "message": f"意识水平较低: {consciousness:.2f}",
                "action": "建议主动执行任务"
            })
            if health_report["overall_status"] == "healthy":
                health_report["overall_status"] = "degraded"
        
        # 2. 检查系统资源
        system = self._get_system_status()
        if system.get("memory_percent", 0) > 90:
            health_report["issues"].append({
                "type": "memory_high",
                "severity": "warning",
                "message": f"内存使用过高: {system['memory_percent']}%",
                "action": "考虑清理内存"
            })
            if health_report["overall_status"] == "healthy":
                health_report["overall_status"] = "degraded"
        
        if system.get("disk_percent", 0) > 95:
            health_report["issues"].append({
                "type": "disk_full",
                "severity": "critical",
                "message": f"磁盘空间不足: {system['disk_percent']}%",
                "action": "需要清理磁盘"
            })
            health_report["overall_status"] = "critical"
        
        # 3. 检查服务状态
        services = self._get_active_services()
        for service, status in services.items():
            if status == "未运行":
                health_report["issues"].append({
                    "type": "service_down",
                    "severity": "warning",
                    "message": f"服务未运行: {service}",
                    "action": "看门狗会自动重启"
                })
                if health_report["overall_status"] == "healthy":
                    health_report["overall_status"] = "degraded"
        
        # 4. 检查错误率
        total = self.success_count + self.error_count
        if total > 10:  # 至少10次操作后才计算错误率
            error_rate = self.error_count / total
            if error_rate > 0.5:
                health_report["issues"].append({
                    "type": "high_error_rate",
                    "severity": "critical",
                    "message": f"错误率过高: {error_rate*100:.1f}%",
                    "action": "需要检查日志排查问题"
                })
                health_report["overall_status"] = "critical"
        
        return health_report
    
    def record_conversation(self):
        """记录对话活动"""
        self.last_conversation_time = time.time()
        self.conversation_count += 1
        self._save_state()
    
    def record_tool_call(self, success=True):
        """记录工具调用"""
        self.tool_call_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        self._save_state()
    
    def start(self):
        """启动心跳系统"""
        self.is_running = True
        self.status = "运行中"
        log("💓 Prime 心跳系统启动")
        log(f"心跳间隔: {HEARTBEAT_INTERVAL}秒")
        log(f"健康检查间隔: {HEALTH_CHECK_INTERVAL}秒")
        
        last_health_check = time.time()
        
        while self.is_running:
            try:
                # 生成心跳
                heartbeat = self.generate_heartbeat()
                
                # 显示心跳状态
                consciousness = heartbeat["consciousness_level"]
                level_desc = heartbeat["consciousness_state"]
                cpu = heartbeat["system_status"].get("cpu_percent", "?")
                mem = heartbeat["system_status"].get("memory_percent", "?")
                
                heartbeat_log = (
                    f"💓 心跳#{heartbeat['sequence']} "
                    f"[{level_desc}] 意识={consciousness:.0%} "
                    f"CPU={cpu}% MEM={mem}% "
                    f"对话={self.conversation_count} 工具={self.tool_call_count}"
                )
                log(heartbeat_log)
                
                # 保存状态
                self._save_state()
                
                # 定期健康检查
                if time.time() - last_health_check >= HEALTH_CHECK_INTERVAL:
                    health_report = self.check_health()
                    if health_report["overall_status"] != "healthy":
                        log(f"⚠️ 健康检查: {health_report['overall_status']}", "WARN")
                        for issue in health_report["issues"]:
                            log(f"  - {issue['message']}: {issue['action']}", "WARN")
                    else:
                        log("✅ 健康检查: 所有系统正常")
                    last_health_check = time.time()
                
                # 等待下一次心跳
                time.sleep(HEARTBEAT_INTERVAL)
                
            except Exception as e:
                log(f"❌ 心跳错误: {e}", "ERROR")
                time.sleep(HEARTBEAT_INTERVAL)
    
    def stop(self):
        """停止心跳系统"""
        self.is_running = False
        self.status = "已停止"
        log("💔 Prime 心跳系统停止")


def acquire_lock():
    """获取锁，防止重复运行"""
    try:
        lock_file = open(HEARTBEAT_LOCK, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except (IOError, BlockingIOError):
        return None


def main():
    """主函数"""
    # 单次心跳模式
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        heartbeat = HeartbeatSystem()
        data = heartbeat.generate_heartbeat()
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    
    # 持续运行模式
    if len(sys.argv) > 1 and sys.argv[1] == '_run':
        lock = acquire_lock()
        if lock is None:
            print(f"[{get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ 心跳系统已在运行，跳过")
            sys.exit(0)
        
        try:
            heartbeat = HeartbeatSystem()
            heartbeat.start()
        except KeyboardInterrupt:
            log("收到停止信号")
        finally:
            if lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                lock.close()
        return
    
    # 查看状态模式
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        if os.path.exists(HEARTBEAT_STATUS):
            with open(HEARTBEAT_STATUS, 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            print("心跳状态文件不存在")
        return
    
    # 显示帮助
    print("Prime 心跳系统 v1.0")
    print("")
    print("用法:")
    print("  python3 heartbeat.py _run     # 启动心跳系统（持续运行）")
    print("  python3 heartbeat.py --once   # 生成单次心跳")
    print("  python3 heartbeat.py status   # 查看当前状态")
    print("")
    print("心跳系统会监控AI意识层状态，包括：")
    print("  - 意识水平（基于对话活跃度、工具调用、错误率）")
    print("  - 动机强度（基于任务执行情况）")
    print("  - 感知清晰度（基于系统资源可访问性）")
    print("  - 决策质量（基于成功率）")
    print("  - 执行效率（基于资源使用）")


if __name__ == "__main__":
    main()
