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

# 夜间时段定义（用于睡眠周期制）
NIGHT_START_HOUR = 21  # 晚上9点
NIGHT_END_HOUR = 5     # 凌晨5点

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
    
    def parse_time(self, time_str):
        """解析时间字符串，支持多种格式"""
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S"
        ]
        for fmt in formats:
            try:
                return datetime.datetime.strptime(time_str, fmt)
            except:
                continue
        return None
    
    def is_in_night_period(self, dt):
        """检查时间是否在夜间时段（21:00-05:00）
        
        夜间时段跨越午夜：
        - 21:00-24:00（当天晚上）
        - 00:00-05:00（次日凌晨）
        """
        hour = dt.hour
        return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR
    
    def find_sleep_in_time_range(self, start_dt, end_dt, must_in_night=True):
        """在指定时间范围内查找睡觉记录
        
        Args:
            start_dt: 范围起始时间
            end_dt: 范围结束时间
            must_in_night: 是否必须在夜间时段（21:00-05:00）
            
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
                sleep_dt = self.parse_time(start_time_str)
                
                if not sleep_dt:
                    continue
                
                # 检查是否在时间范围内
                if sleep_dt < start_dt or sleep_dt > end_dt:
                    continue
                
                # 如果要求必须在夜间时段
                if must_in_night and not self.is_in_night_period(sleep_dt):
                    continue
                
                # 取最新的
                if last_sleep_time is None or sleep_dt > last_sleep_time:
                    last_sleep_time = sleep_dt
        
        return last_sleep_time
    
    def find_sleep_cycle_start(self):
        """根据当前时间找到睡眠周期的起始点
        
        时段睡眠周期制：
        - 只有在夜间时段（21:00-05:00）的"睡觉了"才算新一天的起始
        - 凌晨0-5点：找昨晚21点后的睡觉
        - 早晨5-21点：找今天5点前的睡觉，没有则找昨晚21点后的
        - 晚上21-24点：找今天5点前的睡觉
        
        Returns:
            datetime: 当前睡眠周期的起始时间
        """
        now = datetime.datetime.now()
        hour = now.hour
        
        if hour < NIGHT_END_HOUR:
            # 凌晨 0-5 点：找昨晚 21 点后的睡觉
            last_night_start = now.replace(hour=NIGHT_START_HOUR, minute=0, second=0, microsecond=0) - datetime.timedelta(days=1)
            sleep_start = self.find_sleep_in_time_range(last_night_start, now, must_in_night=True)
            return sleep_start
            
        elif hour < NIGHT_START_HOUR:
            # 白天 5-21 点：先找今天 5 点前的睡觉，再找昨晚 21 点后的
            today_early = now.replace(hour=NIGHT_END_HOUR, minute=0, second=0, microsecond=0)
            
            # 先找今天凌晨的睡觉
            sleep_start = self.find_sleep_in_time_range(today_early - datetime.timedelta(hours=NIGHT_END_HOUR), today_early, must_in_night=True)
            
            if sleep_start:
                return sleep_start
            
            # 再找昨晚的睡觉
            last_night_start = now.replace(hour=NIGHT_START_HOUR, minute=0, second=0, microsecond=0) - datetime.timedelta(days=1)
            sleep_start = self.find_sleep_in_time_range(last_night_start, now, must_in_night=True)
            return sleep_start
            
        else:
            # 晚上 21-24 点：找今天凌晨的睡觉
            today_early = now.replace(hour=NIGHT_END_HOUR, minute=0, second=0, microsecond=0)
            sleep_start = self.find_sleep_in_time_range(today_early - datetime.timedelta(hours=NIGHT_END_HOUR), today_early, must_in_night=True)
            return sleep_start
    
    def find_sleep_cycle_for_date(self, date):
        """找到指定日期的睡眠周期
        
        Args:
            date: 目标日期
            
        Returns:
            (start_dt, end_dt): 周期的开始和结束时间
        """
        # 该日期的睡眠周期：前一天晚上21点后的睡觉 → 该日期晚上21点后的睡觉
        # 或者更准确：前一天夜间时段的睡觉 → 该日期夜间时段的睡觉
        
        night_before_start = datetime.datetime.combine(date - datetime.timedelta(days=1), datetime.time(NIGHT_START_HOUR, 0, 0))
        night_start = datetime.datetime.combine(date, datetime.time(NIGHT_START_HOUR, 0, 0))
        
        # 周期开始：前一天夜间的睡觉
        cycle_start = self.find_sleep_in_time_range(night_before_start, night_start + datetime.timedelta(hours=8), must_in_night=True)
        
        # 周期结束：当天夜间的睡觉
        cycle_end = self.find_sleep_in_time_range(night_start, night_start + datetime.timedelta(hours=8), must_in_night=True)
        
        return cycle_start, cycle_end
    
    def handle_report(self, period='today'):
        """获取统计报表 - 支持自然天和时段睡眠周期制
        
        统计周期：
        - natural_today: 自然天，今天 00:00 → 现在
        - today: 时段睡眠周期制，最近一次夜间（21:00-05:00）睡觉 → 现在
        - yesterday: 时段睡眠周期制，前一天的睡眠周期
        - week/total: 按开始时间判断
        
        返回结构化数据，方便前端使用
        """
        try:
            if not os.path.exists(LOG_FILE):
                response = {'error': '目前还没有任何记录数据。'}
            else:
                stats = {}
                now = datetime.datetime.now()
                period_start = None
                period_end = None
                period_type = "standard"
                
                # 计算统计边界
                if period == "natural_today":
                    # 自然天：今天 00:00 → 现在
                    today_date = now.date()
                    period_start = datetime.datetime.combine(today_date, datetime.time(0, 0, 0))
                    period_end = now
                    period_type = "natural_day"
                    
                elif period == "yesterday":
                    # 时段睡眠周期制 - 昨天
                    yesterday_date = (now - datetime.timedelta(days=1)).date()
                    period_start, period_end = self.find_sleep_cycle_for_date(yesterday_date)
                    period_type = "sleep_cycle"
                    
                    if not period_start:
                        response = {'error': '没有找到睡眠记录来确定统计周期（需要前一天夜间21:00-05:00的睡觉记录）'}
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
                        return
                        
                elif period == "today":
                    # 时段睡眠周期制 - 今天
                    period_start = self.find_sleep_cycle_start()
                    period_end = now
                    period_type = "sleep_cycle"
                    
                    if not period_start:
                        response = {'error': '没有找到睡眠记录来确定统计周期（需要夜间21:00-05:00的睡觉记录）'}
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
                        return
                
                with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        start_time_str = row['开始时间']
                        end_time_str = row.get('结束时间', '')
                        start_dt = self.parse_time(start_time_str)
                        end_dt = self.parse_time(end_time_str) if end_time_str else None
                        
                        if not start_dt:
                            continue
                        
                        cat = row['类别']
                        
                        if period in ["today", "yesterday", "natural_today"] and period_start and period_end:
                            if not end_dt:
                                end_dt = start_dt
                            effective_start = max(start_dt, period_start)
                            effective_end = min(end_dt, period_end)
                            if effective_end > effective_start:
                                sec = int((effective_end - effective_start).total_seconds())
                                stats[cat] = stats.get(cat, 0) + sec
                        else:
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
                    total_sec = sum(stats.values())
                    period_info = ""
                    if period in ["today", "yesterday", "natural_today"] and period_start and period_end:
                        start_str = period_start.strftime("%m-%d %H:%M")
                        end_str = period_end.strftime("%m-%d %H:%M") if period == "yesterday" else "现在"
                        if period == "natural_today":
                            cycle_type = "自然天"
                        else:
                            cycle_type = "时段睡眠周期制（21:00-05:00）"
                        period_info = f"\n**统计周期：{start_str} → {end_str}**（{cycle_type}）\n"
                    
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
                    
                    response = {
                        'report': '\n'.join(report_lines),
                        'period': period,
                        'period_type': period_type,
                        'period_start': period_start.isoformat() if period_start else None,
                        'period_end': period_end.isoformat() if period_end else None,
                        'total_seconds': total_sec,
                        'categories': stats
                    }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode())
    
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
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode())
    
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
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode())

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
