# Operit AI 时间记录助手 - 增强版

基于 Operit AI 的时间记录助手，完全模仿 aTimeLogger 的功能，通过 Python 脚本 + CSV 文件实现，支持强大的统计和可视化功能。

## 🌟 功能特性

- 🕐 **任务记录**：开始、停止任务记录
- 🔄 **自动切换**：自动结束上一个任务，开始新任务
- 📊 **智能统计**：今日、本周、总统计，带占比分析
- 📈 **可视化图表**：饼图、柱状图生成
- 📄 **数据存储**：CSV 格式，兼容 Excel
- 🎯 **语音支持**：支持语音指令（如"开始睡觉"、"今天统计"）
- 🌐 **中文支持**：完全支持中文任务名称
- 🧠 **意图识别**：自动识别同义词，智能合并相似任务
- 🧹 **乌龙清理**：自动检测并删除短时错误任务

## 📁 文件结构

```
/home/operit/
├── time_tracker.py         # 核心时间记录脚本
├── visualize_stats.py      # 可视化图表生成脚本
├── time_log.csv            # 历史数据存储
├── current_task.json       # 当前任务状态
├── synonyms.json           # 同义词配置文件
├── enhanced_test.py         # 增强版测试脚本
├── simple_test.py          # 简单测试脚本
├── system_prompt_template.txt # 系统提示词模板
└── README.md               # 使用说明
```

> **📋 项目管理说明**：本项目采用类似 Git 的版本管理方式，所有重要修改都会在 README 的开发日志中记录。修改代码前请先阅读 README，备份原文件，并经过确认后再操作。

## 🚀 核心函数

### time_tracker.py

#### start_task(task_name)
开始记录任务
- 自动结束当前正在运行的任务
- **意图识别**：自动匹配同义词，合并到正确的类别
- **乌龙清理**：检测并删除上一条短时错误任务
- 记录新任务开始时间
- 更新 current_task.json

#### find_best_category(user_input)
**意图识别功能（新增）**
- 同义词匹配：根据 `synonyms.json` 配置映射任务名称
- 模糊匹配：计算字符串相似度，识别相似任务名
- 时长优先：多个相似任务时，选择历史时长最长的类别

**匹配优先级：**
1. 同义词表精确匹配（最高优先级）
2. 同义词表模糊匹配
3. 已有类别精确匹配
4. 已有类别模糊匹配（按时长排序）
5. 创建新类别

#### check_oolong_task(new_task_name)
**乌龙任务检测（新增）**
- 检测条件：
  - 上一任务持续时间 < 60 秒
  - 上一任务与新任务名称相似度 ≥ 60%
  - 上一任务结束时间在 5 分钟内
- 自动删除乌龙任务记录

#### stop_current_task()
停止当前任务
- 计算任务持续时间
- 将记录写入 time_log.csv
- 清除当前任务状态

#### get_report(period="today")
**核心统计功能**
- period 参数：`today`（今日）、`week`（本周）、`total`（总统计）
- 返回 Markdown 格式的统计表格
- 包含类别、时长、占比信息

#### get_daily_stats()
获取今日统计（保持向后兼容）

#### get_all_stats()
获取总统计（保持向后兼容）

### visualize_stats.py

#### generate_pie_chart(period="today")
生成时间分布饼图
- 自动过滤小于1%的项目
- 高质量 PNG 输出
- 包含详细图例

#### generate_bar_chart(period="today")
生成时间分布柱状图
- 显示具体时长数值
- 高质量 PNG 输出

## 🎯 使用方法

### 1. 系统提示词配置

复制 `system_prompt_template.txt` 的内容到 Operit AI 的系统提示词中。

### 2. 语音指令示例

#### 开始任务
- "开始睡觉" → 调用 start_task("睡觉")
- "开始工作" → 调用 start_task("工作")  
- "开始学习" → 调用 start_task("学习")
- "开始运动" → 调用 start_task("运动")

#### 停止任务
- "停止" → 调用 stop_current_task()
- "结束" → 调用 stop_current_task()

#### 统询功能
- "今天统计" → 调用 get_report("today")
- "本周统计" → 调用 get_report("week")
- "总统计" → 调用 get_report("total")
- "今天时间都花哪了？" → 调用 get_report("today")
- "这周做了什么？" → 调用 get_report("week")

#### 可视化
- "看饼图" → 调用 generate_pie_chart("today")
- "看本周饼图" → 调用 generate_pie_chart("week")
- "看总统计饼图" → 调用 generate_pie_chart("total")
- "显示柱状图" → 调用 generate_bar_chart("today")

## 📊 统计输出示例

### 今日统计表格
```
### 📊 时间统计报表 (today)
| 类别 | 时长 | 占比 |
| :--- | :--- | :--- |
| 工作 | 3h 0m | 75.0% |
| 睡觉 | 1h 0m | 25.0% |

**总计消耗：4小时0分钟**
```

### 可视化图表
- 饼图：显示各类别时间占比
- 柱状图：显示各类别具体时长
- 图片自动保存为 PNG 格式

## 🧪 测试

### 基础测试
```bash
python simple_test.py
```

### 增强测试（包含统计和可视化）
```bash
python enhanced_test.py
```

### 手动测试脚本功能
```bash
# 开始任务
python3 ~/time_tracker.py start "测试任务"

# 停止任务
python3 ~/time_tracker.py stop

# 查看统计
python3 ~/time_tracker.py report today
python3 ~/time_tracker.py report week
python3 ~/time_tracker.py report total

# 生成饼图
python3 ~/visualize_stats.py pie today
python3 ~/visualize_stats.py pie week
python3 ~/visualize_stats.py pie total

# 生成柱状图
python3 ~/visualize_stats.py bar today
```

## 📈 数据格式

### CSV 文件格式 (time_log.csv)
```csv
类别,开始时间,结束时间,持续秒数,格式化时长
工作,2024-01-01 09:00:00,2024-01-01 12:00:00,10800,3:00:00
睡觉,2024-01-01 12:00:00,2024-01-01 13:00:00,3600,1:00:00
学习,2024-01-01 13:00:00,2024-01-01 15:00:00,7200,2:00:00
```

### 当前任务状态 (current_task.json)
```json
{
    "task_name": "工作",
    "start_time": "2024-01-01 09:00:00"
}
```

## 🔧 进阶功能

### 1. 数据同步
可以扩展脚本，添加 API 调用将数据同步到：
- Notion
- Google Sheets
- Excel Online
- 数据库

### 2. 定时提醒
添加定时功能，提醒用户记录时间或休息。

### 3. 地理位置触发
利用 Operit AI 的 GPS 能力，根据位置自动提示开始任务。

### 4. 数据分析
添加更高级的数据分析功能：
- 时间趋势分析
- 效率评估
- 目标达成度

## ⚠️ 注意事项

- 确保 Python 环境正常工作
- 文件路径使用绝对路径 ~/time_log.csv
- CSV 文文件使用 UTF-8-SIG 编码，Excel 兼容
- 定期备份 time_log.csv 数据
- 支持任意中文任务名称，无需预定义

## 🎉 使用场景

1. **日常时间管理**：记录每天的时间分配
2. **工作效率分析**：分析工作、学习、休息时间比例
3. **习惯养成**：跟踪特定活动的时间投入
4. **项目时间统计**：记录不同项目的时间消耗
5. **生活平衡**：平衡工作、学习、娱乐、休息时间

## 📞 支持

遇到问题请检查：
1. Python 脚本是否正常运行
2. CSV 文件路径是否正确
3. 系统提示词是否正确配置
4. 数据文件是否有读写权限

---

## 🐛 常见问题与解决方案

### 0. 数据库损坏/数据丢失问题

**问题描述**：
- SQLite 数据库 `time_data.db` 文件存在，但数据丢失或损坏
- 数据库中仅有少量测试数据，历史记录全部丢失
- Web 界面和统计功能依赖 CSV 文件，导致数据不一致

**现象示例**：
```bash
# 数据库只有 2 条记录
sqlite3 /home/operit/time_data.db "SELECT COUNT(*) FROM time_log;"
# 输出: 2

# 但 CSV 文件有 96 条完整记录
wc -l /home/operit/time_log.csv
# 输出: 97 (含标题行)
```

**解决方法**：

**方案一：从 CSV 恢复到数据库**
```python
import sqlite3
import csv
from datetime import datetime

DB_PATH = "/home/operit/time_data.db"
CSV_PATH = "/home/operit/time_log.csv"

# 清空并重建数据表
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("DELETE FROM time_log")

# 从 CSV 导入数据
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        c.execute("""
            INSERT INTO time_log (start_time, end_time, task_name, category)
            VALUES (?, ?, ?, ?)
        """, (row['开始时间'], row['结束时间'], row['类别'], row['类别']))

conn.commit()
print(f"已恢复 {c.rowcount} 条记录")
```

**方案二：改用 CSV 作为主数据源**
- 本项目最终采用 CSV 文件作为主数据存储
- `time_tracker.py` 直接读写 `time_log.csv`
- 数据库仅作为可选的备份方案

**预防措施**：
1. 定期备份 CSV 文件到多个位置（如 `/sdcard/Backup/`）
2. 使用 `export_to_csv.py` 导出每日数据
3. 考虑实现自动备份脚本

**教训**：
- SQLite 虽然方便，但在嵌入式设备上可能因意外断电、存储问题导致损坏
- CSV 文件更健壮，易于恢复和人工检查
- 建议采用"CSV为主 + 数据库可选"的架构

---

### 1. 路径问题：`~` 符号在不同用户下指向不同目录

**问题描述**：
- `time_tracker.py` 使用 `os.path.expanduser("~")` 获取用户主目录
- 以 root 用户执行时，`~` 指向 `/root/`，而非预期的 `/home/operit/`
- 导致找不到 CSV 文件，统计数据为空

**解决方法**：
```python
# 错误写法
BASE_DIR = os.path.expanduser("~")

# 正确写法 - 使用绝对路径
BASE_DIR = "/home/operit"
```

**教训**：在多用户环境下运行的脚本，应使用绝对路径而非 `~`。

---

### 2. 时间格式兼容问题

**问题描述**：
- `time_tracker.py` 原只支持 `%Y-%m-%d %H:%M:%S` 格式
- 但 CSV 中存储的是 ISO 格式（如 `2026-02-25T02:03:59.427199`）
- 导致 `datetime.strptime()` 解析失败，抛出 `ValueError`

**解决方法**：
```python
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
```

**教训**：时间解析应支持多种格式，增强兼容性。

---

### 3. CSV 数据列缺失问题

**问题描述**：
- 部分 CSV 记录只有 3 列（类别、开始时间、结束时间）
- 缺少"持续秒数"和"格式化时长"两列
- 导致统计时 `row['持续秒数']` 返回空值，`int()` 转换失败

**解决方法**：
- 手动计算缺失的持续时间字段
- 用 Python 脚本批量更新 CSV 文件：
```python
import csv
from datetime import datetime

def parse_time(time_str):
    formats = ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间: {time_str}")

# 读取并修复 CSV
with open('time_log.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

for row in rows:
    if not row.get('持续秒数') or row['持续秒数'] == '':
        start = parse_time(row['开始时间'])
        end = parse_time(row['结束时间'])
        duration = end - start
        row['持续秒数'] = str(int(duration.total_seconds()))
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        row['格式化时长'] = f"{hours}:{minutes:02d}:{seconds:02d}"
```

**教训**：数据写入时应确保所有字段完整，定期检查数据完整性。

---

### 4. Web 界面时区显示问题

**问题描述**：
- 系统时区为 UTC，比北京时间慢 8 小时
- Web 界面显示的时间被浏览器按本地时区解析
- 例如：UTC 17:00 被显示为"下午5点"而非北京时间的"凌晨1点"

**解决方法**：
- 在 `web_status.json` 中使用带时区的 ISO 格式：
```json
{
  "timestamp": "2026-03-02T21:00:00+08:00",
  "timezone": "Asia/Shanghai (UTC+8)"
}
```

- Python 代码中指定时区：
```python
from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))
timestamp = datetime.now(BEIJING_TZ).isoformat()
# 输出: "2026-03-03T01:09:15+08:00"
```

**教训**：涉及时间的应用应始终使用带时区的 ISO 格式，避免歧义。

---

### 5. 负数时长问题

**问题描述**：
- 停止任务时，系统时间与开始时间存在偏差
- 例如：开始时间是 UTC 20:42，但停止时系统时间变成了 UTC 17:03
- 导致 `end_time - start_time` 为负数，CSV 记录显示 `"-1 day, 20:21:23"`

**解决方法**：
1. 删除错误的负数时长记录
2. 确保系统时间同步
3. 在停止任务时添加时间校验：
```python
def stop_current_task():
    # ... 解析开始时间 ...
    end_time = datetime.now()
    duration = end_time - start_time
    
    # 校验：持续时间不能为负
    if duration.total_seconds() < 0:
        raise ValueError(f"错误：结束时间早于开始时间，请检查系统时间！")
    
    # ... 继续写入 CSV ...
```

**教训**：时间计算应添加合理性校验，防止异常数据污染。

---

### 6. Web 数据不同步问题

**问题描述**：
- Web 界面的 `web_status.json` 与实际 CSV 数据不一致
- 两个系统独立运行，数据未同步更新

**解决方法**：
- 每次任务开始/停止时，同时更新 `web_status.json`
- 或创建定时同步脚本：
```python
import csv
import json
from datetime import datetime, timezone, timedelta

def sync_web_status():
    # 读取 CSV 统计数据
    stats = calculate_stats_from_csv()
    
    # 读取当前任务状态
    with open('current_task.json', 'r') as f:
        current_task = json.load(f)
    
    # 生成 web_status.json
    web_status = {
        "task_name": current_task.get('task_name', '无任务'),
        "timestamp": current_task.get('start_time', ''),
        "running": True if current_task else False,
        "stats": stats,
        "timezone": "Asia/Shanghai (UTC+8)"
    }
    
    with open('web_status.json', 'w', encoding='utf-8') as f:
        json.dump(web_status, f, ensure_ascii=False, indent=2)
```

**教训**：多系统共享数据时，应建立统一的数据同步机制。

---

### 7. 数据修复完整流程

当遇到数据问题时，可按以下步骤排查修复：

```bash
# 1. 检查 CSV 文件格式
head -5 /home/operit/time_log.csv

# 2. 检查字段完整性
python3 -c "
import csv
with open('/home/operit/time_log.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if not row.get('持续秒数'):
            print(f'第{i+1}行缺少持续秒数')
"

# 3. 检查时间格式
python3 -c "
import csv
from datetime import datetime
with open('/home/operit/time_log.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            datetime.strptime(row['开始时间'], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            print(f\"异常时间格式: {row['开始时间']}\")
"

# 4. 重新生成统计数据
python3 /home/operit/time_tracker.py report total
```

---


---

## 📝 开发日志

详细的开发日志已迁移到 [CHANGELOG.md](CHANGELOG.md)，包含所有功能更新、问题修复和技术细节。

### 最近更新
- **2026-03-11**: Proot监控卡死问题与看门狗解决方案
- **2026-03-10**: 监控服务Proot环境兼容问题修复、任务锁定功能
- **2026-03-06**: 任务锁定功能（吃饭/睡觉时暂停监控）
- **2026-03-04**: 开机自启动与任务切换通知
