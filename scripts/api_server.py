import json
import csv
import datetime
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 配置
BASE_DIR = '/home/operit'
LOG_FILE = os.path.join(BASE_DIR, "time_log.csv")
STATE_FILE = os.path.join(BASE_DIR, "current_task.json")

class TimeTrackerAPI(BaseHTTPRequestHandler):
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
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def handle_report(self, period='today'):
        """获取统计报表"""
        try:
            if not os.path.exists(LOG_FILE):
                response = {'error': '目前还没有任何记录数据。'}
            else:
                stats = {}
                now = datetime.datetime.now()
                
                with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 支持两种时间格式
                        start_time_str = row['开始时间']
                        start_dt = None
                        for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]:
                            try:
                                start_dt = datetime.datetime.strptime(start_time_str, fmt)
                                break
                            except:
                                continue
                        
                        if not start_dt:
                            continue  # 跳过解析失败的行
                        
                        # 过滤逻辑
                        is_match = False
                        if period == "today" and start_dt.date() == now.date():
                            is_match = True
                        elif period == "week" and (now - start_dt).days < 7:
                            is_match = True
                        elif period == "total":
                            is_match = True
                        
                        if is_match:
                            cat = row['类别']
                            sec = int(row['持续秒数'])
                            stats[cat] = stats.get(cat, 0) + sec

                if not stats:
                    response = {'error': f'在 {period} 范围内没有找到记录。'}
                else:
                    # 格式化输出
                    total_sec = sum(stats.values())
                    report_lines = [
                        f"### 📊 时间统计报表 ({period})",
                        "| 类别 | 时长 | 占比 |",
                        "| :--- | :--- | :--- |"
                    ]
                    
                    for cat, sec in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                        h = sec // 3600
                        m = (sec % 3600) // 60
                        percent = (sec / total_sec) * 100
                        report_lines.append(f"| {cat} | {h}h {m}m | {percent:.1f}% |")
                    
                    report_lines.append(f"**总计消耗：{total_sec // 3600}小时{(total_sec % 3600) // 60}分钟**")
                    response = {'report': '\n'.join(report_lines)}
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def handle_start(self, task_name):
        """开始任务"""
        try:
            if not task_name:
                response = {'error': '任务名称不能为空'}
            else:
                # 这里应该调用实际的start_task函数
                # 为了简化，我们直接创建状态文件
                now = datetime.datetime.now()
                state = {
                    "task_name": task_name,
                    "start_time": now.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                with open(STATE_FILE, 'w') as f:
                    json.dump(state, f)
                
                response = {
                    'success': True,
                    'message': f'已开始记录：{task_name}',
                    'start_time': state['start_time']
                }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
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
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
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