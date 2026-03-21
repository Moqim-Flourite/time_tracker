import json
import csv
import datetime
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 配置
BASE_DIR = '/home/operit'
LOG_FILE = os.path.join(BASE_DIR, "time_log.csv")
STATE_FILE = os.path.join(BASE_DIR, "current_task.json")

class TimeTrackerAPI(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        """添加CORS头，允许跨域访问"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        """处理预检请求"""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/time/current' or path == '/api/current-task':
            self.handle_current_task()
        elif path == '/api/time/report' or path == '/api/report':
            self.handle_report(parse_qs(parsed_path.query).get('period', ['today'])[0])
        elif path == '/api/time/start' or path == '/api/start':
            task_name = parse_qs(parsed_path.query).get('task', [''])[0]
            self.handle_start(task_name)
        elif path == '/api/time/stop' or path == '/api/stop':
            self.handle_stop()
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def handle_current_task(self):
        """获取当前任务状态"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    
                    if state.get('task_name') and state.get('start_time'):
                        response = {
                            'status': 'running',
                            'task_name': state['task_name'],
                            'start_time': state['start_time']
                        }
                    else:
                        response = {
                            'status': 'idle',
                            'task_name': '',
                            'start_time': None
                        }
            else:
                response = {
                    'status': 'idle',
                    'task_name': '',
                    'start_time': None
                }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def find_last_sleep_time(self, before_date=None):
        """找到指定日期之前最后一次睡觉任务的开始时间
        
        Args:
            before_date: 截止日期（不含该日），None表示找最新的睡觉记录
            
        Returns:
            datetime: 最后一次睡觉的开始时间，如果没有返回None
        """
        last_sleep_time = None
        
        if not os.path.exists(LOG_FILE):
            return None
            
        with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cat = row.get('类别', '')
                if cat != '睡觉':
                    continue
                    
                start_time_str = row.get('开始时间', '')
                start_dt = None
                
                for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        start_dt = datetime.datetime.strptime(start_time_str, fmt)
                        break
                    except:
                        continue
                        
                if not start_dt:
                    continue
                    
                # 如果指定了截止日期，检查是否在范围内
                if before_date:
                    if start_dt.date() < before_date:
                        if last_sleep_time is None or start_dt > last_sleep_time:
                            last_sleep_time = start_dt
                else:
                    if last_sleep_time is None or start_dt > last_sleep_time:
                        last_sleep_time = start_dt
        
        return last_sleep_time
    
    def handle_report(self, period='today'):
        """获取统计报表（睡眠周期制统计）
        
        统计周期：
        - today: 从昨天晚上睡觉 → 现在
        - yesterday: 从前天晚上睡觉 → 昨天晚上睡觉
        - week/total: 保持原逻辑
        """
        try:
            if not os.path.exists(LOG_FILE):
                response = {'error': '目前还没有任何记录数据。'}
            else:
                stats = {}
                now = datetime.datetime.now()
                
                # 计算睡眠周期边界
                if period == "yesterday":
                    # 昨天 = 前天晚上睡觉 → 昨天晚上睡觉
                    yesterday_date = (now - datetime.timedelta(days=1)).date()
                    day_before_yesterday = (now - datetime.timedelta(days=2)).date()
                    
                    # 找昨天最后一次睡觉的开始时间（周期结束）
                    day_end = self.find_last_sleep_time(before_date=yesterday_date + datetime.timedelta(days=1))
                    # 找前天最后一次睡觉的开始时间（周期开始）
                    day_start = self.find_last_sleep_time(before_date=yesterday_date)
                    
                    if not day_start or not day_end:
                        response = {'error': f'没有找到睡眠记录来确定统计周期，请确保有睡眠记录'}
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode())
                        return
                        
                elif period == "today":
                    # 今天 = 昨天晚上睡觉 → 现在
                    today_date = now.date()
                    day_start = self.find_last_sleep_time(before_date=today_date)
                    day_end = now
                    
                    if not day_start:
                        response = {'error': f'没有找到睡眠记录来确定统计周期，请确保有睡眠记录'}
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode())
                        return
                else:
                    day_start = None
                    day_end = None
                
                with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 支持两种时间格式
                        start_time_str = row['开始时间']
                        end_time_str = row.get('结束时间', '')
                        start_dt = None
                        end_dt = None
                        
                        for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                            try:
                                if not start_dt:
                                    start_dt = datetime.datetime.strptime(start_time_str, fmt)
                                if end_time_str and not end_dt:
                                    end_dt = datetime.datetime.strptime(end_time_str, fmt)
                            except:
                                continue
                        
                        if not start_dt:
                            continue  # 跳过解析失败的行
                        
                        cat = row['类别']
                        
                        # 对于today和yesterday，使用跨日分摊逻辑
                        if period in ["today", "yesterday"] and day_start and day_end:
                            # 计算该记录落在目标日期的时间
                            if not end_dt:
                                end_dt = start_dt  # 没有结束时间则跳过
                            
                            # 计算交集（记录时间 ∩ 目标日期）
                            effective_start = max(start_dt, day_start)
                            effective_end = min(end_dt, day_end)
                            
                            if effective_end > effective_start:
                                sec = int((effective_end - effective_start).total_seconds())
                                stats[cat] = stats.get(cat, 0) + sec
                        else:
                            # week和total保持原逻辑（按开始时间判断）
                            is_match = False
                            if period == "week" and (now - start_dt).days < 7:
                                is_match = True
                            elif period == "total":
                                is_match = True
                            
                            if is_match:
                                sec = int(row['持续秒数'])
                                stats[cat] = stats.get(cat, 0) + sec

                if not stats:
                    response = {'error': f'在 {period} 范围内没有找到记录。'}
                else:
                    # 格式化输出
                    total_sec = sum(stats.values())
                    
                    # 生成周期信息
                    period_info = ""
                    if period in ["today", "yesterday"] and day_start and day_end:
                        start_str = day_start.strftime("%m-%d %H:%M")
                        end_str = day_end.strftime("%m-%d %H:%M") if period == "yesterday" else "现在"
                        period_info = f"\n**统计周期：{start_str} → {end_str}**（睡眠周期制）\n"
                    
                    report_lines = [
                        f"### 📊 时间统计报表 ({period})",
                        period_info,
                        "| 类别 | 时长 | 占比 |",
                        "| :--- | :--- | :--- |"
                    ]
                    
                    for cat, sec in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                        h = sec // 3600
                        m = (sec % 3600) // 60
                        percent = (sec / total_sec) * 100
                        report_lines.append(f"| {cat} | {h}h {m}m | {percent:.1f}% |")
                    
                    report_lines.append(f"\n**总计消耗：{total_sec // 3600}小时{(total_sec % 3600) // 60}分钟**")
                    response = {'report': '\n'.join(report_lines)}
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def handle_start(self, task_name):
        """开始任务"""
        try:
            if not task_name:
                response = {'error': '任务名称不能为空'}
            else:
                # 先停止当前正在运行的任务（写入CSV）
                stop_msg = ""
                if os.path.exists(STATE_FILE):
                    try:
                        with open(STATE_FILE, 'r') as f:
                            old_state = json.load(f)
                        old_start = datetime.datetime.strptime(old_state['start_time'], "%Y-%m-%d %H:%M:%S")
                        old_end = datetime.datetime.now()
                        old_duration = old_end - old_start
                        
                        # 写入CSV
                        file_exists = os.path.isfile(LOG_FILE)
                        with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
                            writer = csv.writer(f)
                            if not file_exists:
                                writer.writerow(["类别", "开始时间", "结束时间", "持续秒数", "格式化时长"])
                            writer.writerow([
                                old_state['task_name'],
                                old_state['start_time'],
                                old_end.strftime("%Y-%m-%d %H:%M:%S"),
                                int(old_duration.total_seconds()),
                                str(old_duration).split('.')[0]
                            ])
                        stop_msg = f"已停止：{old_state['task_name']}，用时{str(old_duration).split('.')[0]}。"
                    except Exception as e:
                        print(f"停止旧任务失败: {e}")
                
                # 创建新任务
                now = datetime.datetime.now()
                state = {
                    "task_name": task_name,
                    "start_time": now.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                with open(STATE_FILE, 'w') as f:
                    json.dump(state, f)
                
                response = {
                    'success': True,
                    'message': f'{stop_msg}已开始记录：{task_name}',
                    'start_time': state['start_time']
                }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def handle_stop(self):
        """停止任务"""
        try:
            if not os.path.exists(STATE_FILE):
                response = {'error': '没有运行中的任务'}
            else:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                
                if not state.get('task_name') or not state.get('start_time'):
                    response = {'error': '没有运行中的任务'}
                else:
                    # 计算持续时间
                    start_time = datetime.datetime.strptime(state['start_time'], "%Y-%m-%d %H:%M:%S")
                    end_time = datetime.datetime.now()
                    duration = end_time - start_time
                    
                    # 写入CSV
                    file_exists = os.path.isfile(LOG_FILE)
                    with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["类别", "开始时间", "结束时间", "持续秒数", "格式化时长"])
                        
                        writer.writerow([
                            state['task_name'],
                            state['start_time'],
                            end_time.strftime("%Y-%m-%d %H:%M:%S"),
                            int(duration.total_seconds()),
                            str(duration).split('.')[0]
                        ])
                    
                    # 删除状态文件
                    os.remove(STATE_FILE)
                    
                    response = {
                        'success': True,
                        'message': f'已结束：{state["task_name"]}，用时：{str(duration).split(".")[0]}',
                        'duration': str(duration).split('.')[0]
                    }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, TimeTrackerAPI)
    print(f"时间记录API服务器启动在端口 {port}")
    print(f"访问 http://localhost:{port} 查看网页界面")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("服务器关闭")
        httpd.shutdown()

if __name__ == '__main__':
    import sys
    # 支持 --port 8080 或直接 8080 两种格式
    port = 8080
    args = sys.argv[1:]
    if '--port' in args:
        idx = args.index('--port')
        if idx + 1 < len(args):
            port = int(args[idx + 1])
    elif args and args[0].isdigit():
        port = int(args[0])
    run_server(port)