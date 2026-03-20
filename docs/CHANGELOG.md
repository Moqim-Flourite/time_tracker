# 时间记录助手 - 开发日志

> 本文件记录所有功能更新、问题修复和技术细节。

---

## 📝 开发日志

### 2026-03-03 Web 统计标签跳转问题修复

**问题现象**：在 Web 界面查看"本周"或"总计"统计时，页面会自动跳转回"今日"

**问题原因**：
- `updatePageStatus()` 每 10 秒自动刷新页面状态
- 刷新时硬编码显示 `'today'`，覆盖了用户选择的标签

**解决方案**：
1. 添加 `currentPeriod` 变量记住用户当前选择的统计周期
2. 点击标签时更新 `currentPeriod`
3. 定时刷新时使用 `this.currentPeriod` 而非硬编码值

**修改文件**：`index.html`

**修改内容**：
```javascript
// 添加变量
const WebStatusDisplay = {
    currentPeriod: 'today',  // 新增：记住用户选择
    // ...
}

// 点击标签时更新
initStatsTabs() {
    tab.addEventListener('click', () => {
        this.currentPeriod = tab.dataset.period;  // 新增
        // ...
    });
}

// 定时刷新时使用
this.updateStatsDisplay(status.stats, this.currentPeriod);  // 修改
```

---

### 2026-03-03 意图识别与乌龙清理功能

**新增功能**：

1. **意图识别（同义词匹配）**
   - 新增 `synonyms.json` 配置文件，存储任务类别同义词
   - `find_best_category()` 函数：智能匹配用户输入到正确的任务类别
   - 匹配优先级：同义词表 > 已有类别 > 新建类别
   - 时长优先：多个相似任务时，自动选择历史时长最长的类别

2. **乌龙任务自动清理**
   - `check_oolong_task()` 函数：检测并删除短时错误任务
   - 判断条件：持续<60秒 + 名称相似>60% + 5分钟内
   - 解决"分享日程"vs"分享日常"等输错词问题

**使用示例**：
```bash
# 说"上班"自动记录为"工作"（同义词匹配）
python3 time_tracker.py start "上班"
# 输出: ✅ 已开始记录：工作（识别：上班 → 工作）

# 输错后立即改正，自动删除错误记录
python3 time_tracker.py start "分享日程"  # 输错了
python3 time_tracker.py start "分享日常"  # 2秒后改正
# 输出: ✅ 已开始记录：分享日常
#       🧹 检测到乌龙任务「分享日程」，已自动删除。
```

**配置文件** (`synonyms.json`)：
```json
{
    "工作": ["上班", "干活", "办公", "打工", "搬砖"],
    "睡觉": ["休息", "睡眠", "睡觉觉", "补觉"],
    "学习": ["看书", "读书", "学习知识", "充电"],
    "运动": ["健身", "锻炼", "跑步", "游泳"]
}
```

**参数配置**：
- `OOLONG_MAX_DURATION = 60` - 乌龙任务最大持续时间（秒）
- `OOLONG_TIME_WINDOW = 300` - 检测时间窗口（秒）
- `SIMILARITY_THRESHOLD = 0.6` - 相似度阈值

---

### 2026-03-03 数据修复记录

**问题现象**：Web 界面显示异常，仅显示"0h9m"，历史数据丢失

**排查过程**：
1. 发现 CSV 文件中 96 条记录有 95 条缺少"持续秒数"字段
2. 发现 `time_tracker.py` 路径问题导致读取错误文件
3. 发现时间格式不兼容导致解析失败
4. 发现时区问题导致时间显示错误

**修复结果**：
- 成功恢复 138 小时 34 分钟的历史数据
- 修复时间格式兼容性
- 修正 Web 界面时区显示
- 添加数据完整性校验

---

---

### 2026-03-03 跨日任务分摊与时区修复

**问题现象**：
1. Web界面今日统计缺少凌晨时段的记录（时区问题）
2. 跨日任务（如22:50-00:40）的时长全部计入开始日期，结束日期统计缺失

**问题原因**：
1. 系统时间为UTC，比北京时间慢8小时，`start_task.py`使用系统时间计算日期边界
2. 原统计逻辑按任务开始日期计算整个任务时长，未处理跨零点分摊

**解决方案**：

**1. 时区修复** - 使用北京时间计算日期边界：
```python
def get_current_time():
    """获取当前时间，转换为北京时间（UTC+8）"""
    timestamp = time.time()
    utc_time = datetime.fromtimestamp(timestamp)
    beijing_time = utc_time + timedelta(hours=8)
    return beijing_time
```

**2. 跨日任务分摊** - 遍历任务涉及的每一天，单独计算当天时长：
```python
# 处理跨日任务：按天分摊时间
current_day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)

while current_day_start < end_time:
    next_day_start = current_day_start + timedelta(days=1)
    
    # 计算在当前天的时长
    day_start = max(start_time, current_day_start)
    day_end = min(end_time, next_day_start)
    day_seconds = int((day_end - day_start).total_seconds())
    
    if day_seconds > 0:
        day_date = current_day_start.date()
        # 判断属于哪个统计周期
        if day_date == today_start.date():
            add_to_stats(category, day_seconds, "today")
        # ... 其他周期判断 ...
    
    current_day_start = next_day_start
```

**修改文件**：`start_task.py`
- 新增 `get_current_time()` 函数获取北京时间
- 重写 `calculate_statistics()` 函数支持跨日分摊

**测试结果**：
- 跨日任务 `调ai 22:50-00:40` 正确分摊：
  - 3月2日：4200秒（70分钟）
  - 3月3日：2400秒（40分钟）✅

---

### 2026-03-03 App智能检测功能

**功能说明**：
- 根据当前使用的App自动推断活动类别
- 支持自动切换任务（可配置最小间隔）
- Operit AI应用（com.ai.assistance.operit）默认忽略，因为使用Operit = 调ai

**使用方法**：
```bash
# 查看当前任务状态
python3 app_detect.py status

# 检测指定App并自动切换（需要传入包名）
python3 app_detect.py detect com.tencent.mm

# 手动切换任务
python3 app_detect.py switch 工作

# 查看App映射配置
python3 app_detect.py mappings
```

**App映射配置** (`app_detect.py`):
```python
APP_MAPPINGS = {
    "com.tencent.mm": "刷手机",           # 微信
    "com.tencent.mobileqq": "刷手机",      # QQ
    "com.ss.android.ugc.aweme": "刷手机",  # 抖音
    "com.tencent.tmgp.sgame": "打游戏",    # 王者荣耀
    "com.ai.assistance.operit": "调ai",    # Operit AI
    "com.tencent.wemeet.app": "工作",      # 腾讯会议
    # ... 更多映射见脚本
}

# 忽略的包名（不触发切换）
IGNORE_PACKAGES = {
    "com.ai.assistance.operit",  # Operit AI - 默认就是调ai
}
```

**配置参数**：
- `MIN_SWITCH_INTERVAL = 300` - 最小切换间隔（秒），防止频繁切换
- `IGNORE_PACKAGES` - 忽略的包名集合

**集成方式**：
Operit AI 在每次用户交互时，通过 `get_page_info` 获取当前App包名，然后调用：
```python
python3 app_detect.py detect <package_name>
```

**日志记录**：
- App使用记录存储在 `app_usage_log.json`
- 保留最近500条记录

---

### 2026-03-03 App智能检测与后台监控

**功能说明**：
- 根据当前使用的App自动推断活动类别
- **支持熄屏检测**：熄屏时自动切换到"熄屏"任务
- 支持后台定时监控（通过工作流，每30秒检测一次）
- Operit AI应用映射到"调ai"
- 支持自动切换任务（最小间隔5分钟保护）

**App映射配置** (`app_detect.py`):
```python
APP_MAPPINGS = {
    # 社交类
    "com.tencent.mm": "刷手机",           # 微信
    "com.tencent.mobileqq": "刷手机",      # QQ
    # 短视频类
    "com.ss.android.ugc.aweme": "刷手机",  # 抖音
    "com.smile.gifmaker": "刷手机",        # 快手
    # 视频类
    "tv.danmaku.bili": "刷手机",           # B站（国内版）
    "com.bilibili.app.in": "刷手机",       # B站（国际版）
    # 游戏类
    "com.tencent.tmgp.sgame": "打游戏",    # 王者荣耀
    "com.miHoYo.Yuanshen": "打游戏",       # 原神
    # AI相关
    "com.ai.assistance.operit": "调ai",    # Operit AI
    # 工作类
    "com.tencent.wemeet.app": "工作",      # 腾讯会议
    "com.alibaba.android.rimet": "工作",   # 钉钉
    # ... 更多映射见脚本
}
```

**配置参数** (`app_detect.py`):
- `MIN_SWITCH_INTERVAL = 300` - 最小切换间隔（秒），防止频繁切换
- `SCREEN_OFF_CATEGORY = "熄屏"` - 熄屏时的任务类别

**使用方法**：
```bash
# 查看当前任务状态
python3 app_detect.py status

# 检测屏幕状态
python3 app_detect.py screen

# 检测指定App（含熄屏检测）
python3 app_detect.py detect com.tencent.mm

# 手动切换任务
python3 app_detect.py switch 工作

# 查看App映射配置
python3 app_detect.py mappings
```

**工作流配置**：
- 名称：App自动检测（含熄屏）
- 触发：每30秒自动执行
- 流程：检测屏幕状态 → 熄屏则切换"熄屏"任务 → 亮屏则检测App并切换

**熄屏检测逻辑**：
1. 使用 `dumpsys display` 获取屏幕状态
2. `mScreenState=ON` → 亮屏，按App映射处理
3. `mScreenState=OFF` → 熄屏，切换到"熄屏"任务

**日志文件**：
- `app_usage_log.json` - App使用记录
- `screen_state.json` - 屏幕状态缓存（备用）

---

---

### 2026-03-03 活动备注功能

**功能说明**：
- 支持在任务名称之外添加详细备注
- 例如：说"洗澡"时记录类别"洗漱"+ 备注"洗澡"
- App检测时自动添加App名称作为备注

**使用方法**：
```bash
# 带备注启动任务
python3 start_task.py 洗漱 洗澡
# 记录：类别=洗漱，备注=洗澡

# App检测自动备注
# 当检测到B站时，自动记录：类别=刷手机，备注=B站
python3 app_detect.py detect com.bilibili.app.in
# 记录：类别=刷手机，备注=B站国际版
```

**数据格式更新**：
- CSV新增"备注"列：`类别,开始时间,结束时间,持续秒数,格式化时长,备注`
- `current_task.json`新增`note`字段

**App名称映射** (`app_detect.py`):
```python
APP_NAMES = {
    "com.tencent.mm": "微信",
    "com.tencent.mobileqq": "QQ",
    "com.ss.android.ugc.aweme": "抖音",
    "tv.danmaku.bili": "B站",
    "com.bilibili.app.in": "B站国际版",
    "com.tencent.tmgp.sgame": "王者荣耀",
    "com.ai.assistance.operit": "Operit",
    # ... 更多映射见脚本
}
```

**查看备注**：
- 备注保存在CSV中，总结报告会显示详细信息
- Web界面不显示备注，保持简洁

---

### 2026-03-03 总结功能

**功能说明**：
- 支持按时间段生成统计总结
- 自动生成AI评价与时间管理建议
- 支持每日自动总结（10点执行）

**使用方法**：
```bash
# 今日总结
python3 summary.py today

# 昨日总结（用于每日自动触发）
python3 summary.py yesterday

# 本周总结
python3 summary.py week

# 本月总结
python3 summary.py month

# 本年总结
python3 summary.py year

# 总计总结
python3 summary.py total
```

**输出示例**：
```
==================================================
📅 昨日时间统计详细报告
生成时间：2026-03-03 10:00:00
==================================================

📊 总记录时长：8小时30分钟
📝 记录条数：15条

--------------------------------------------------
📋 各类别详细记录：
--------------------------------------------------

【刷手机】总计：3h20m (39.2%)
----------------------------------------
  1. 03-02 12:00~15:20 (3h 20m) [B站]

【工作】总计：2h30m (29.4%)
----------------------------------------
  1. 03-02 09:00~11:30 (2h 30m)

==================================================
📊 昨日时间分配分析

⏱️ 总记录时长：8小时30分钟

📋 时间分配详情：
  • 刷手机：3h20m (39.2%)
  • 工作：2h30m (29.4%)
  • 睡觉：2h0m (23.5%)

💡 AI评价与建议：
  ⚠️ 生产力时间较少(29.4%)，建议增加专注工作时间。
  😴 休息时间充足(23.5%)，注意保持规律作息。
  🎮 娱乐时间较多(39.2%)，建议适当控制。
==================================================
💾 报告已保存：/home/operit/reports/daily_2026-03-02.txt
```

**自动总结工作流**：
- 工作流名称：每日时间总结（10点）
- 触发时间：每天上午10:00
- 自动执行：`python3 summary.py yesterday`
- 报告保存：`/home/operit/reports/daily_YYYY-MM-DD.txt`

**手动触发**：
- 周总结：`python3 summary.py week`
- 月总结：`python3 summary.py month`
- 年总结：`python3 summary.py year`
- 总计：`python3 summary.py total`

---

**享受您的时间管理之旅！** 🚀

---

### 2026-03-03 活动备注功能

**功能说明**：
- 支持在任务名称之外添加详细备注
- 例如：说"洗澡"时记录类别"洗漱"+ 备注"洗澡"
- App检测时自动添加App名称作为备注

**使用方法**：
```bash
# 带备注启动任务
python3 start_task.py 洗漱 洗澡
# 记录：类别=洗漱，备注=洗澡

# App检测自动备注
# 当检测到B站时，自动记录：类别=刷手机，备注=B站
python3 app_detect.py detect com.bilibili.app.in
# 记录：类别=刷手机，备注=B站国际版
```

**数据格式更新**：
- CSV新增"备注"列：`类别,开始时间,结束时间,持续秒数,格式化时长,备注`
- `current_task.json`新增`note`字段

**App名称映射** (`app_detect.py`):
```python
APP_NAMES = {
    "com.tencent.mm": "微信",
    "com.tencent.mobileqq": "QQ",
    "com.ss.android.ugc.aweme": "抖音",
    "tv.danmaku.bili": "B站",
    "com.bilibili.app.in": "B站国际版",
    "com.tencent.tmgp.sgame": "王者荣耀",
    "com.ai.assistance.operit": "Operit",
    # ... 更多映射见脚本
}
```

**查看备注**：
- 备注保存在CSV中，总结报告会显示详细信息
- Web界面不显示备注，保持简洁

---

### 2026-03-03 总结功能

**功能说明**：
- 支持按时间段生成统计总结
- 自动生成AI评价与时间管理建议
- 支持每日自动总结（10点执行）

**使用方法**：
```bash
# 今日总结
python3 summary.py today

# 昨日总结（用于每日自动触发）
python3 summary.py yesterday

# 本周总结
python3 summary.py week

# 本月总结
python3 summary.py month

# 本年总结
python3 summary.py year

# 总计总结
python3 summary.py total
```

**输出内容**：
1. **详细报告**：各类别时间分布、具体记录（含备注）
2. **AI评价**：
   - 生产力时间占比分析与建议
   - 休息时间占比分析与建议
   - 娱乐时间占比分析与建议

**示例输出**：
```
==================================================
📅 今日时间统计详细报告
生成时间：2026-03-03 03:11:06
==================================================

📊 总记录时长：3小时40分钟
📝 记录条数：12条

--------------------------------------------------
📋 各类别详细记录：
--------------------------------------------------

【调ai】总计：2h49m (76.8%)
----------------------------------------
  1. 03-02 22:50~00:40 (1h 50m)
  2. 03-03 01:54~02:27 (33m 1s) [Operit]
  ...

==================================================
📊 今日时间分配分析

⏱️ 总记录时长：3小时40分钟

📋 时间分配详情：
  • 调ai：2h49m (76.8%)
  • 洗漱：0h30m (13.6%)
  • 睡觉：0h7m (3.5%)

💡 AI评价与建议：
  ⚠️ 生产力时间较少(0.0%)，建议增加专注工作时间。
  ⚠️ 休息时间偏少(3.5%)，注意劳逸结合。
  ✨ 娱乐时间控制良好(3.1%)。
==================================================

💾 报告已保存：/home/operit/reports/today_20260303_031106.txt
```

**工作流配置**：
- 名称：每日时间总结（10点）
- 触发：每天上午10点自动执行
- 动作：生成昨日总结报告
- 报告保存路径：`/home/operit/reports/`
### 2026-03-03 辅助应用白名单功能

**功能说明**：
- 当正在进行某项活动时，打开白名单中的应用不会触发状态切换
- 例如：正在"睡觉"时打开宝可梦睡眠/网易云音乐 → 保持"睡觉"状态
- 这些应用是"辅助"当前活动的，不应改变主活动类别

**配置位置** (`app_detect.py`):
```python
ASSISTANT_APPS = {
    "睡觉": [
        "jp.pokemon.pokemonsleep",  # 宝可梦睡眠 - 睡眠追踪
        "com.netease.cloudmusic",  # 网易云音乐 - 听歌睡觉
        "com.kugou.android",       # 酷狗音乐
        "com.kuwo.player",         # 酷我音乐
        "tv.danmaku.bili",         # 哔哩哔哩 - 放海浪声等助眠音频
        "com.bilibili.app.in",     # B站国际版
        "com.mi.health",           # 小米健康 - 睡眠监测
        "com.huawei.health",       # 华为健康 - 睡眠监测
    ],
    "学习": [
        "com.eusoft.eudic",        # 欧路词典 - 查单词
        "com.eusoft.ting.en",      # 每日英语听力
        "com.duolingo",            # 多邻国
        "com.shici",               # 诗词
        "com.bf.words_recite",     # 背单词
    ],
    "工作": [
        "com.tencent.androidqqmail",              # QQ邮箱 - 查邮件
        "com.google.android.apps.docs.editors.sheets",  # Google表格
        "cn.wps.moffice_eng.xiaomi.lite",         # WPS
        "cn.wps.note",                            # WPS笔记
    ],
}
```

**使用示例**：
```bash
# 正在睡觉时打开网易云音乐
python3 app_detect.py detect com.netease.cloudmusic
# 检测类别: 刷手机
# 未切换: 辅助应用白名单（睡觉时使用网易云音乐）

# 正在睡觉时打开微信
python3 app_detect.py detect com.tencent.mm
# 检测类别: 刷手机
# 已自动切换任务 → 切换到"刷手机"
```

**查看白名单配置**：
```bash
python3 app_detect.py assistants
```

**添加新应用**：
直接编辑 `app_detect.py` 中的 `ASSISTANT_APPS` 字典，按活动类别添加应用包名。

**应用场景**：
- **睡觉**：睡眠追踪App、音乐App（助眠白噪音）、健康监测App
- **学习**：词典、翻译工具、笔记App
- **工作**：邮箱、文档工具、会议软件

**设计理念**：
- 这些应用是"辅助"当前活动的，不应触发状态切换
- 区别于"主要活动"：打开微信刷朋友圈是主要活动，切换到"刷手机"
- 区别于"次要活动"：睡觉时听歌是辅助，保持"睡觉"状态

---

### 2026-03-04 启用后台自动监控服务

**功能说明**：
- 启用 `app_monitor_auto.py` 作为后台守护进程
- 每30秒自动检测前台App并切换任务
- 无需AI交互即可自动记录时间

**服务管理命令**：
```bash
# 启动后台监控
python3 /home/operit/app_monitor_auto.py start

# 停止监控
python3 /home/operit/app_monitor_auto.py stop

# 查看状态
python3 /home/operit/app_monitor_auto.py status

# 修改配置
python3 /home/operit/app_monitor_auto.py set interval 60      # 检测间隔
python3 /home/operit/app_monitor_auto.py set min_switch_interval 120  # 最小切换间隔
```

**当前配置**：
- 检测间隔：30秒
- 最小切换间隔：60秒
- 日志文件：`/home/operit/app_monitor_auto.log`
- PID文件：`/home/operit/app_monitor_auto.pid`

**工作原理**：
1. 后台进程每30秒调用 `dumpsys activity activities` 获取前台App
2. 根据App映射表推断活动类别
3. 自动调用 `start_task.py` 切换任务
4. 熄屏时切换到"熄屏"任务

**注意事项**：
- 进程通过 `nohup` 在后台运行，终端关闭不影响
- 重启设备后需要手动重新启动
- 可考虑配置 `systemd` 服务或 `crontab` 实现开机自启

---

### 2026-03-04 开机自启动与任务切换通知

**功能说明**：
1. **开机自启动**：通过 crontab `@reboot` 实现设备重启后自动启动监控服务
2. **任务切换通知**：任务切换时发送手机通知，告知当前状态

**开机自启动配置**：

创建了启动脚本 `/home/operit/start_monitor.sh`：
```bash
#!/bin/bash
# 等待系统完全启动（30秒）
sleep 30
cd /home/operit
python3 /home/operit/app_monitor_auto.py start
```

配置 crontab：
```bash
# 编辑crontab
crontab -e

# 添加以下行
@reboot /home/operit/start_monitor.sh
```

**任务切换通知实现**：

由于 Ubuntu 后台进程无法直接调用 Android 通知命令，采用**队列桥接模式**：

1. **通知队列**：`/sdcard/OperitNotifications/notification_queue.json`
   - Ubuntu 后台进程（`app_monitor_auto.py`、`start_task.py`）写入通知到队列
   - Android 端工作流每分钟检查队列并发送通知

2. **通知发送脚本**：`/sdcard/OperitNotifications/send_notifications.sh`
   - 使用 `cmd notification post` 命令发送通知
   - 需要 Shizuku 权限

3. **工作流配置**：
   - 名称：通知发送服务
   - 触发：每60秒定时执行
   - 命令：`sh /sdcard/OperitNotifications/send_notifications.sh`

**通知格式**：
- 标题：`🔄 任务切换` 或 `📺 熄屏检测`
- 内容：`已切换到: {任务名}`

**文件位置**：
- 通知队列：`/sdcard/OperitNotifications/notification_queue.json`
- 发送日志：`/sdcard/OperitNotifications/notification_sent.log`
- 发送脚本：`/sdcard/OperitNotifications/send_notifications.sh`

**注意事项**：
- 设备重启后需要重新授权 Shizuku，否则通知发送可能失败
- 监控服务通过 crontab 自动启动，无需手动干预
- 通知队列使用共享存储目录 `/sdcard/`，确保 Ubuntu 和 Android 都能访问

---

### 2026-03-10 监控服务 Proot 环境兼容问题修复

**问题现象**：
- 应用切换时任务不自动切换
- 手机通知消失
- 监控日志显示"无法获取前台App（可能熄屏）"

**根本原因**：
监控服务使用了错误的脚本版本。`app_monitor_auto.py` 尝试通过 `dumpsys` 命令获取前台App，但在 Proot/Ubuntu 环境中无法执行 Android 系统命令。

**Operit 环境架构说明**：

| 环境 | 路径特征 | 能力 | 运行内容 |
|------|----------|------|----------|
| Android 原生 | `/sdcard/...` | 可执行 dumpsys、am 等系统命令 | 工作流脚本 |
| Proot/Ubuntu | `/home/operit/...` | Python 脚本、后台服务 | 监控服务 |
| 共享存储 | `/sdcard/OperitNotifications/` | 两边都可访问 | 通信桥梁 |

**正确的监控脚本选择**：

- ❌ `app_monitor_auto.py` - 直接调用 dumpsys，Proot 环境无效
- ✅ `app_monitor_v2.py` - 从文件读取前台App信息，正确方式

**Proot 环境权限问题修复**：

`os.kill(pid, 0)` 在 Proot 环境会报 `PermissionError`，需改用 `/proc/{pid}` 检查进程：

```python
def is_process_running(pid):
    """检查进程是否运行（兼容Proot环境）"""
    try:
        return os.path.exists(f"/proc/{pid}")
    except:
        return False
```

**服务管理命令**：
```bash
# 启动监控（正确版本）
python3 /home/operit/app_monitor_v2.py start

# 停止监控
python3 /home/operit/app_monitor_v2.py stop

# 查看状态
python3 /home/operit/app_monitor_v2.py status
```

**正确的监控架构**：
```
┌─────────────────────┐     写入     ┌────────────────────────┐
│ Android端工作流      │ ──────────→ │ current_app.txt        │
│ (monitor_app.sh)    │             │ /sdcard/Operit...      │
│ 使用 dumpsys        │             └──────────┬─────────────┘
└─────────────────────┘                        │ 读取
                     ┌──────────────────────────┘
                     ▼
┌─────────────────────┐     调用     ┌────────────────────────┐
│ app_monitor_v2.py   │ ──────────→ │ app_detect.py          │
│ (Proot端监控)        │             │ (任务检测与切换)         │
│ 从文件读取App信息    │              └────────────────────────┘
└─────────────────────┘
```

**注意事项**：
- 不要使用 `app_monitor_auto.py`，它在 Proot 环境无法工作
- Android 端工作流需保持运行以更新 `current_app.txt`
- 设备重启后需重新启动监控服务

---

### 2026-03-10 通知发送工作流缺失问题修复

**问题现象**：
- 任务切换后手机没有收到通知
- 通知队列 `/sdcard/OperitNotifications/notification_queue.json` 有堆积的未发送通知
- 发送日志 `notification_sent.log` 停止更新

**根本原因**：
通知发送工作流不存在！之前的工作流可能被删除或从未创建，导致通知无法从队列发送到手机。

**解决方法**：

创建"通知发送服务"工作流：
```json
{
  "name": "通知发送服务",
  "description": "每60秒检查通知队列并发送手机通知",
  "nodes": [
    {"id": "trigger", "type": "trigger", "triggerType": "schedule", 
     "triggerConfig": {"enabled": "true", "interval_ms": "60000", "repeat": "true", "schedule_type": "interval"}},
    {"id": "manual_trigger", "type": "trigger", "triggerType": "manual"},
    {"id": "send_notification", "type": "execute", "actionType": "super_admin:shell",
     "actionConfig": {"command": "sh /sdcard/OperitNotifications/send_notifications.sh"}}
  ],
  "connections": [
    {"sourceNodeId": "trigger", "targetNodeId": "send_notification", "condition": "on_success"},
    {"sourceNodeId": "manual_trigger", "targetNodeId": "send_notification", "condition": "on_success"}
  ]
}
```

**通知架构**：
```
┌─────────────────────┐     写入通知     ┌────────────────────────┐
│ app_monitor_v2.py   │ ──────────────→ │ notification_queue.json│
│ (Proot端监控)        │                 │ /sdcard/Operit...      │
└─────────────────────┘                 └──────────┬─────────────┘
                                                   │ 读取
                     ┌─────────────────────────────┘
                     ▼
┌─────────────────────┐     发送通知     ┌────────────────────────┐
│ 通知发送工作流       │ ──────────────→ │ 手机通知栏              │
│ (Android端, 60秒)   │   cmd notification│                        │
└─────────────────────┘   (需要Shizuku)  └────────────────────────┘
```

**相关文件**：
- 通知队列：`/sdcard/OperitNotifications/notification_queue.json`
- 发送脚本：`/sdcard/OperitNotifications/send_notifications.sh`
- 发送日志：`/sdcard/OperitNotifications/notification_sent.log`

**注意事项**：
- 通知发送需要 Shizuku 权限
- 设备重启后需重新授权 Shizuku
- 工作流 ID: `1e8462ad-59f3-4023-877c-b83dca96babf`

---

### 2026-03-06 任务锁定功能（吃饭/睡觉时暂停监控）

**功能说明**：
- 当用户手动切换到"吃饭"或"睡觉"任务时，自动监控暂停
- 用户说"吃完了"、"睡醒了"等短语时，自动解锁监控
- 防止吃饭/睡觉期间因打开其他App而错误切换任务

**锁定任务列表** (`start_task.py`):
```python
LOCKED_TASKS = ["吃饭", "睡觉"]
```

**解锁短语**：
```python
UNLOCK_PHRASES = [
    "吃完了", "吃饱了", "吃好了", "吃完饭了",
    "睡醒了", "起床了", "醒了", "不睡了", "起醒了",
    "好了", "结束了", "完了"
]
```

**使用示例**：
```bash
# 开始吃饭 → 监控锁定
python3 start_task.py 吃饭
# 输出: 🔒 监控已锁定：吃饭（自动监控暂停，说"吃完了/睡醒了"解锁）

# 吃饭期间打开微信 → 不触发切换
# （监控检测到锁定状态，跳过自动切换）

# 吃完了 → 监控解锁
python3 start_task.py 吃完了
# 输出: 🔓 检测到解锁短语：吃完了
#       ✅ 监控已解锁，自动监控恢复正常
```

**工作原理**：

1. **锁定机制**：
   - `start_task.py` 在切换到"吃饭/睡觉"时，写入 `monitor_lock.json`:
   ```json
   {
       "locked": true,
       "task_name": "吃饭",
       "lock_time": "2026-03-06T12:30:00+08:00",
       "reason": "用户切换到锁定任务: 吃饭"
   }
   ```

2. **监控检测**：
   - `app_monitor_v2.py` 每次检测前检查 `monitor_lock.json`
   - 如果 `locked=true`，跳过自动切换，继续睡眠等待

3. **解锁机制**：
   - 用户说"吃完了"时，`start_task.py` 检测到解锁短语
   - 清空锁定状态，恢复自动监控

**修改文件**：
- `/home/operit/start_task.py` - 添加锁定/解锁逻辑
- `/home/operit/app_monitor_v2.py` - 检查锁定状态
- `/home/operit/monitor_lock.json` - 锁定状态文件（运行时生成）

**使用场景**：
- 吃饭时看手机 → 保持"吃饭"状态，不切换到"刷手机"
- 睡觉时开宝可梦睡眠 → 保持"睡觉"状态
- 睡醒后说"睡醒了" → 恢复自动监控

**注意事项**：
- 锁定仅对自动监控生效，用户手动切换任务不受影响
- 切换到非锁定任务（如"工作"）时自动解锁
- 解锁短语不区分大小写

---

### 2026-03-11 Proot监控卡死问题与看门狗解决方案

**问题现象**：
用户反馈13:35-14:00熄屏睡觉，但时间记录显示熄屏时间只有0秒。Android监控日志正确显示熄屏，但Proot监控未处理。

**根本原因**：
Proot监控进程（app_monitor_v2.py）在运行过程中卡死，不再读取和处理Android监控写入的事件。

**解决方案**：

创建看门狗脚本 `/home/operit/watchdog_monitor.py`：

```python
#!/usr/bin/env python3
"""
监控看门狗 - 检查 Proot 监控是否正常运行，异常则重启
使用方法：
  python3 watchdog_monitor.py           # 单次检查
  python3 watchdog_monitor.py _run      # 持续运行（每分钟检查）
  
建议：通过 crontab 每分钟执行一次
"""

# 核心检测逻辑：
# 1. 检查进程是否存在
# 2. 检查日志文件更新时间（超过120秒未更新视为异常）
# 3. 检查Android监控文件更新时间（超过300秒未更新视为异常）
# 4. 异常时自动重启监控
```

**配置crontab自动运行**：
```bash
# 添加看门狗到 crontab（每分钟检查一次）
(crontab -l 2>/dev/null; echo "* * * * * python3 /home/operit/watchdog_monitor.py >> /home/operit/watchdog.log 2>&1") | crontab -

# 当前 crontab 配置：
# 0 0 * * * /home/operit/time_sync.sh          # 每天时间同步
# @reboot /home/operit/start_monitor.sh        # 开机启动监控
# * * * * * python3 /home/operit/watchdog_monitor.py  # 看门狗（每分钟）
```

**看门狗检测项目**：

| 检查项 | 阈值 | 动作 |
|--------|------|------|
| Proot 监控进程 | 不存在 | 自动重启 |
| 监控日志更新 | 静默 > 120秒 | 自动重启 |
| Android 监控文件 | 静默 > 300秒 | 记录警告 |

**使用方法**：
```bash
# 单次检查
python3 /home/operit/watchdog_monitor.py

# 持续运行模式
python3 /home/operit/watchdog_monitor.py _run

# 查看日志
tail -f /home/operit/watchdog.log
```

**相关文件**：
- 看门狗脚本：`/home/operit/watchdog_monitor.py`
- 看门狗日志：`/home/operit/watchdog.log`
- Proot监控：`/home/operit/app_monitor_v2.py`
- Android监控：`/sdcard/monitor_android.sh`

**注意事项**：
- 看门狗每分钟检查一次，监控最长中断时间为2分钟
- 建议定期检查看门狗日志确认监控状态
- 如监控频繁卡死，需排查Proot环境或内存问题

---

### 2026-03-10 通知即时发送优化

**问题现象**：
- Web界面任务已切换，但手机通知显示旧任务
- 通知发送延迟大（原来是队列轮询，每60秒发送一次）

**根本原因**：
通知机制采用"写入队列 + 轮询发送"模式，存在延迟问题。

**解决方案**：
改为"任务切换时直接发送"模式，无需队列轮询。

**修改内容** (`start_task.py`):
```python
def send_notification(title, content):
    """直接发送通知到手机（通过Shizuku/cmd）"""
    NOTIFICATION_LOG = "/sdcard/OperitNotifications/notification_sent.log"
    try:
        # 直接通过 cmd notification post 发送通知（需要Shizuku权限）
        result = subprocess.run(
            ['cmd', 'notification', 'post', '-t', title, 'app_monitor', content],
            capture_output=True, text=True, timeout=10
        )
        
        # 记录日志
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        with open(NOTIFICATION_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] 发送: {title} - {content}\n")
        
        if result.returncode == 0:
            print(f"📢 通知已发送: {title}")
            return True
        else:
            print(f"⚠️ 通知发送失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"⚠️ 通知发送异常: {e}")
        return False
```

**通知架构变化**：
```
旧架构（有延迟）:
┌─────────────────────┐     写入队列     ┌─────────────────────┐
│ start_task.py       │ ─────────────→  │ notification_queue  │
└─────────────────────┘                  └──────────┬──────────┘
                                                     │ 每60秒轮询
                                         ┌──────────▼──────────┐
                                         │ 通知发送工作流       │
                                         │ (Android端)         │
                                         └──────────┬──────────┘
                                                     │
                                         ┌──────────▼──────────┐
                                         │ 手机通知栏           │
                                         └─────────────────────┘

新架构（即时发送）:
┌─────────────────────┐     cmd notification     ┌─────────────────────┐
│ start_task.py       │ ─────────────────────→   │ 手机通知栏           │
│ (Proot端)           │   (通过Shizuku权限)      │                      │
└─────────────────────┘                          └─────────────────────┘
```

**问题发现**：
- `cmd` 命令在 Proot 环境不可用（即使有 Shizuku）
- 只能在 Android 原生环境中执行 `cmd notification post`

**修正方案**：
保持"写入队列 + 工作流发送"机制，但优化轮询间隔：
- 原间隔：60秒
- 新间隔：15秒（最大延迟从60秒降为15秒）

**架构**：
```
┌─────────────────────┐     写入队列     ┌─────────────────────┐
│ start_task.py       │ ─────────────→  │ notification_queue  │
│ (Proot端)           │                 └──────────┬──────────┘
└─────────────────────┘                            │ 每15秒轮询
                                         ┌────────▼──────────┐
                                         │ 通知发送工作流     │
                                         │ (Android端)       │
                                         │ cmd notification   │
                                         └────────┬──────────┘
                                                   │
                                         ┌────────▼──────────┐
                                         │ 手机通知栏         │
                                         └────────────────────┘
```

**注意事项**：
- 需要 Shizuku 权限才能执行 `cmd notification post`
- 设备重启后需重新授权 Shizuku
- 通知延迟最大15秒（工作流轮询间隔）


## 2026-03-18 系统稳定性改进

### 改进内容

1. **看门狗增强** (`watchdog_monitor.py`)
   - 新增cron服务检查和自动启动
   - 新增API服务器检查和自动启动
   - 新增Android监控检查（检测current_app.txt更新时间）
   - 统一服务管理，单次检查所有组件

2. **启动脚本优化** (`start_monitor.sh`)
   - 启动时检查cron、API、监控是否已运行
   - 检测Android监控状态
   - 更清晰的状态输出

3. **架构说明**
   ```
   cron服务（定时任务基础）
     └── 看门狗（每分钟执行）
           ├── 检查cron → 自动启动
           ├── 检查Proot监控 → 自动重启
           ├── 检查API服务器 → 自动启动
           └── 检查Android监控 → 尝试重启
   
   Android端: monitor_app.sh (后台脚本，每10秒更新current_app.txt)
   Proot端: app_monitor_v2.py (读取current_app.txt，切换任务)
   工作流: App自动检测 (30秒间隔，通过get_page_info)
   ```

4. **健康检查脚本** (`full_health_check.sh`)
   - 检查API服务器
   - 检查Proot监控服务
   - 检查当前任务状态
   - 检查日志文件
   - 检查web_status同步
   - 检查Android端监控
   - 检查工作流状态

### 使用方法

```bash
# 手动启动所有服务
./start_monitor.sh

# 手动运行一次健康检查
./full_health_check.sh

# 手动运行一次看门狗检查
python3 watchdog_monitor.py

# 查看看门狗日志
tail -50 /home/operit/watchdog.log
```

### 问题修复

- 修复系统崩溃后cron不自动恢复的问题
- 修复看门狗只检查监控进程不检查cron的问题
- 增加Android监控的状态检测

---

## 2026-03-20 熄屏检测修复 & 看门狗v3.2

### 问题根因
- **Android监控脚本被MIUI杀死**，导致熄屏检测完全失效
- 脚本日志停在3月19日15:44，进程不存在
- 整个熄屏检测链路依赖Android脚本写入SCREEN_OFF

### 熄屏检测三层架构
```
第一层：Operit工作流 → dumpsys display检测mScreenState
第二层：Proot监控 → 读取current_app.txt → SCREEN_OFF时切换任务
第三层：Android脚本 → dumpsys power检测mWakefulness=Asleep → 写入SCREEN_OFF
```

### 修复内容
1. **手动启动Android监控脚本** - 已恢复运行
2. **看门狗升级到v3.2** - 新增Android脚本监控
   - 检查monitor_heartbeat.txt心跳文件
   - 心跳超时180秒自动重启脚本
   - 使用Shizuku权限启动脚本

### 看门狗v3.2新增检查项
- `check_android_monitor()` - 检查Android脚本心跳
- `start_android_monitor()` - 通过Shizuku启动脚本

### 配置参数
- `MAX_ANDROID_MONITOR_SILENCE = 180` - 脚本心跳最大静默时间
- `ANDROID_MONITOR_HEARTBEAT = /sdcard/OperitNotifications/monitor_heartbeat.txt`

### 文件修改
- `/home/operit/watchdog_monitor.py` - 升级到v3.2
- 备份：`/home/operit/watchdog_monitor.py.bak`


---

## 2026-03-20 锁屏检测功能

### 新增功能
1. **锁屏检测** - Android脚本v3.6新增锁屏检测
   - 检测 `mDreamingLockscreen=true` 或 `isKeyguardShowing=true`
   - 锁屏+熄屏/亮屏 都写入 `SCREEN_LOCKED`

2. **任务类别变更** - 熄屏/锁屏统一切换到"空闲"任务
   - `SCREEN_OFF_CATEGORY = "空闲"`
   - 之前是"熄屏"，现在改为"空闲"更准确

### 文件修改
- `/sdcard/OperitNotifications/monitor_app.sh` - 升级到v3.6，添加锁屏检测
- `/home/operit/app_monitor_v2.py` - 支持 `SCREEN_LOCKED` 信号
- `/home/operit/app_detect.py` - 任务类别改为"空闲"

### 检测逻辑
```
mWakefulness=Asleep (熄屏)
├── isKeyguardShowing=true → SCREEN_LOCKED → 空闲
└── isKeyguardShowing=false → SCREEN_OFF → 空闲

mWakefulness=Awake (亮屏)
├── isKeyguardShowing=true → SCREEN_LOCKED → 空闲 (锁屏界面)
└── isKeyguardShowing=false → 正常获取App包名
```


## [2026-03-20 04:19] 修复SCREEN_LOCKED切换失败问题

### 问题
- 熄屏20秒后仍显示"调ai"，切换失败
- 日志报错：`[Errno 2] No such file or directory: 'adb'`

### 根因
1. `check_and_switch`函数对SCREEN_LOCKED调用了`app_detect.py screen`
2. `screen`命令依赖adb且未传递SCREEN_LOCKED参数
3. 监控循环中调用`check_and_switch`时硬编码传"SCREEN_OFF"

### 修复
1. `check_and_switch`对SCREEN_OFF/SCREEN_LOCKED都调用`app_detect.py detect <signal>`
2. 监控循环正确传递实际的package值而非硬编码

### 文件
- `/home/operit/app_monitor_v2.py` - 修复切换逻辑

## [2026-03-20 12:26] 修复Dozing状态未检测问题

### 问题
- 熄屏后仍然显示"调ai"，Android脚本未写入SCREEN_OFF
- MIUI熄屏后进入Dozing（微光）模式，不是Asleep

### 根因
- monitor_app.sh只检测`mWakefulness=Asleep`
- 没有处理`mWakefulness=Dozing`状态

### 修复
- monitor_app.sh v3.6 → v3.7
- 检测条件改为`Asleep\|Dozing`

### 文件
- `/sdcard/OperitNotifications/monitor_app.sh`

## [2026-03-20 17:50] 修复切换间隔配置不生效问题

### 问题
- 在Operit里待了很久仍然是"刷手机"任务
- 监控进程停止了（最后日志停在09:41:06）

### 根因
1. `app_detect.py`的`MIN_SWITCH_INTERVAL`硬编码为300秒(5分钟)
2. 没有读取`app_monitor_config.json`的配置(15秒)
3. 监控进程意外停止

### 修复
- `app_detect.py`现在从配置文件读取`min_switch_interval`
- 默认值改为15秒，与配置文件一致

### 文件
- `/home/operit/app_detect.py`
