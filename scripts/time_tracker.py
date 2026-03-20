import json
import csv
import datetime
import os
from difflib import SequenceMatcher

BASE_DIR = "/home/operit"  # 使用绝对路径，避免root环境下路径错误
LOG_FILE = os.path.join(BASE_DIR, "time_log.csv")
STATE_FILE = os.path.join(BASE_DIR, "current_task.json")
SYNONYMS_FILE = os.path.join(BASE_DIR, "synonyms.json")

# 乌龙任务阈值配置
OOLONG_MAX_DURATION = 60  # 最大持续时间（秒）
OOLONG_TIME_WINDOW = 300  # 时间窗口（秒）- 上一个任务结束到现在的时间
SIMILARITY_THRESHOLD = 0.6  # 相似度阈值

def load_synonyms():
    """加载同义词配置"""
    if os.path.exists(SYNONYMS_FILE):
        with open(SYNONYMS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_synonyms(synonyms):
    """保存同义词配置"""
    with open(SYNONYMS_FILE, 'w', encoding='utf-8') as f:
        json.dump(synonyms, f, ensure_ascii=False, indent=4)

def string_similarity(s1, s2):
    """计算两个字符串的相似度 (0-1)"""
    return SequenceMatcher(None, s1, s2).ratio()

def get_category_stats():
    """获取各类别的历史总时长"""
    if not os.path.exists(LOG_FILE):
        return {}
    
    stats = {}
    with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row['类别']
            sec = int(row.get('持续秒数', 0) or 0)
            stats[cat] = stats.get(cat, 0) + sec
    return stats

def find_best_category(user_input):
    """
    根据用户输入找到最佳匹配的类别
    返回: (best_category, is_new, matched_synonym)
    - best_category: 最终确定的类别名
    - is_new: 是否是新类别
    - matched_synonym: 匹配到的同义词（如果有）
    
    优先级：
    1. 同义词表精确匹配（最高优先级）
    2. 同义词表模糊匹配
    3. 已有类别精确匹配
    4. 已有类别模糊匹配（按时长排序）
    5. 创建新类别
    """
    synonyms = load_synonyms()
    stats = get_category_stats()
    
    # 1. 同义词表精确匹配（最高优先级）
    for main_cat, syn_list in synonyms.items():
        if user_input == main_cat:
            return main_cat, False, None
        if user_input in syn_list:
            return main_cat, False, user_input
    
    # 2. 同义词表模糊匹配
    for main_cat, syn_list in synonyms.items():
        for syn in syn_list:
            similarity = string_similarity(user_input, syn)
            if similarity >= SIMILARITY_THRESHOLD:
                return main_cat, False, user_input
        # 也检查与主类名的模糊匹配
        if string_similarity(user_input, main_cat) >= SIMILARITY_THRESHOLD:
            return main_cat, False, user_input
    
    # 3. 已有类别精确匹配
    if user_input in stats:
        return user_input, False, None
    
    # 4. 已有类别模糊匹配（按时长排序，时长长的优先）
    all_categories = list(stats.keys())
    similar_cats = []
    
    for cat in all_categories:
        similarity = string_similarity(user_input, cat)
        if similarity >= SIMILARITY_THRESHOLD:
            similar_cats.append((cat, similarity, stats[cat]))
    
    if similar_cats:
        # 按时长排序（时长长的优先），再按相似度排序
        similar_cats.sort(key=lambda x: (x[2], x[1]), reverse=True)
        best_cat = similar_cats[0][0]
        return best_cat, False, user_input if best_cat != user_input else None
    
    # 5. 完全没找到匹配，创建新类别
    return user_input, True, None

def check_oolong_task(new_task_name):
    """
    检查并清理乌龙任务
    条件：
    1. 上一任务持续时间 < OOLONG_MAX_DURATION 秒
    2. 上一任务与新任务名称相似
    3. 上一任务刚结束（5分钟内）
    
    返回: (is_oolong, deleted_task_name) 或 (False, None)
    """
    if not os.path.exists(LOG_FILE):
        return False, None
    
    # 读取最后一条记录
    last_record = None
    with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if rows:
            last_record = rows[-1]
    
    if not last_record:
        return False, None
    
    # 检查持续时间
    try:
        duration = int(last_record.get('持续秒数', 0) or 0)
    except:
        return False, None
    
    if duration >= OOLONG_MAX_DURATION:
        return False, None
    
    # 检查时间窗口
    try:
        end_time = parse_time(last_record['结束时间'])
        now = datetime.datetime.now()
        time_diff = (now - end_time).total_seconds()
        if time_diff > OOLONG_TIME_WINDOW:
            return False, None
    except:
        return False, None
    
    # 检查名称相似度
    old_task = last_record['类别']
    similarity = string_similarity(old_task, new_task_name)
    
    if similarity < SIMILARITY_THRESHOLD:
        return False, None
    
    # 确认是乌龙任务，删除最后一条记录
    with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    
    if len(lines) > 1:  # 保留标题行
        with open(LOG_FILE, 'w', encoding='utf-8-sig') as f:
            f.writelines(lines[:-1])
        return True, old_task
    
    return False, None

def start_task(task_name):
    now = datetime.datetime.now()
    
    # 1. 先停止当前正在运行的任务（会写入CSV）
    stop_msg = stop_current_task()
    
    # 2. 检查并清理乌龙任务（停止后才能检测CSV最后一条）
    is_oolong, deleted_task = check_oolong_task(task_name)
    oolong_msg = ""
    if is_oolong:
        oolong_msg = f"\n🧹 检测到乌龙任务「{deleted_task}」，已自动删除。"
    
    # 3. 目的识别：找到最佳匹配的类别
    best_category, is_new, matched_synonym = find_best_category(task_name)
    
    # 4. 开启新任务
    state = {
        "task_name": best_category,
        "start_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "original_input": task_name  # 保存原始输入，便于调试
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)
    
    # 构建返回消息
    msg = f"✅ 已开始记录：{best_category}"
    if matched_synonym:
        msg += f"（识别：{task_name} → {best_category}）"
    elif is_new:
        msg += f"（新类别）"
    msg += f"，开始时间：{state['start_time']}"
    
    if oolong_msg:
        msg += oolong_msg
    
    return msg

def parse_time(time_str):
    """解析时间字符串，支持多种格式"""
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO格式带毫秒
        "%Y-%m-%d %H:%M:%S",      # 标准格式
        "%Y-%m-%dT%H:%M:%S",      # ISO格式不带毫秒
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间: {time_str}")

def stop_current_task():
    if not os.path.exists(STATE_FILE):
        return
    
    with open(STATE_FILE, 'r') as f:
        try:
            state = json.load(f)
        except:
            return

    start_time = parse_time(state['start_time'])
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    
    # 将记录写入 CSV (Excel 可读)
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
            str(duration).split('.')[0] # 格式如 0:30:00
        ])
    
    os.remove(STATE_FILE)
    return f"已结束：{state['task_name']}，用时：{str(duration).split('.')[0]}"

def parse_time(time_str):
    """解析时间字符串，支持多种格式"""
    # 尝试多种时间格式
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO格式带毫秒
        "%Y-%m-%d %H:%M:%S",      # 标准格式
        "%Y-%m-%dT%H:%M:%S",      # ISO格式不带毫秒
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间: {time_str}")

def get_report(period="today"):
    """统计报表：today, week, 或 total"""
    if not os.path.exists(LOG_FILE):
        return "目前还没有任何记录数据。"
    
    stats = {}
    now = datetime.datetime.now()
    
    with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            start_dt = parse_time(row['开始时间'])
            
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
        return f"在 {period} 范围内没有找到记录。"

    # 格式化输出
    total_sec = sum(stats.values())
    report = f"### 📊 时间统计报表 ({period})\n"
    report += "| 类别 | 时长 | 占比 |\n| :--- | :--- | :--- |\n"
    
    for cat, sec in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        h = sec // 3600
        m = (sec % 3600) // 60
        percent = (sec / total_sec) * 100
        report += f"| {cat} | {h}h {m}m | {percent:.1f}% |\n"
    
    report += f"\n**总计消耗：{total_sec // 3600}小时{(total_sec % 3600) // 60}分钟**"
    return report

def get_daily_stats():
    """获取今日统计（保持向后兼容）"""
    return get_report("today")

def get_all_stats():
    """获取总统计（保持向后兼容）"""
    return get_report("total")

# 修改 main 接口
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "start" and len(sys.argv) > 2:
            print(start_task(sys.argv[2]))
        elif cmd == "stop":
            print(stop_current_task() or "没有运行中的任务")
        elif cmd == "report":
            period = sys.argv[2] if len(sys.argv) > 2 else "today"
            print(get_report(period))