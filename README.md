# 🕐 Time Tracker - 时间记录助手

基于 Operit AI 的智能时间记录系统，支持自动App监控、任务切换、统计分析。

## ✨ 功能特性

- 🤖 **自动监控**: 后台自动检测前台App，智能切换任务
- 📱 **熄屏检测**: 支持熄屏、锁屏、Dozing状态检测
- 🔄 **任务切换**: 自动结束上一个任务，开始新任务
- 📊 **智能统计**: 今日、本周、本月、总统计
- 🧠 **意图识别**: 同义词匹配，智能归类任务
- 🌐 **Web界面**: REST API + 静态页面展示
- 🔔 **通知系统**: 任务切换通知推送

## 📁 项目结构

```
time-tracker/
├── scripts/              # 核心脚本
│   ├── time_tracker.py   # 时间记录核心
│   ├── start_task.py     # 任务切换主入口
│   ├── app_detect.py     # App检测与分类
│   ├── app_monitor_v2.py # Proot监控服务
│   ├── watchdog_monitor.py # 看门狗服务
│   ├── api_server.py     # REST API服务器
│   └── *.sh              # Shell脚本
├── config/               # 配置文件
│   ├── app_monitor_config.json  # 监控配置
│   └── synonyms.json     # 同义词映射
├── docs/                 # 文档
│   ├── README.md         # 详细说明
│   └── CHANGELOG.md      # 更新日志
└── web/                  # Web界面(可选)
```

## 🚀 快速开始

### 1. 核心命令

```bash
# 开始任务
python3 start_task.py "工作"

# 查看今日统计
python3 time_tracker.py report today

# 查看本周统计
python3 time_tracker.py report week
```

### 2. 启动监控服务

```bash
# 启动App监控
python3 app_monitor_v2.py start

# 查看状态
python3 app_monitor_v2.py status

# 停止监控
python3 app_monitor_v2.py stop
```

### 3. 启动API服务器

```bash
python3 api_server.py 8080
# 访问 http://localhost:8080/api/time/current
```

## ⚙️ 配置

### app_monitor_config.json

```json
{
  "interval": 10,           // 检测间隔(秒)
  "enabled": true,          // 是否启用
  "ignore_packages": [],    // 忽略的App包名
  "min_switch_interval": 15 // 最小切换间隔(秒)
}
```

### synonyms.json

```json
{
  "工作": ["上班", "干活", "办公"],
  "睡觉": ["休息", "睡眠", "补觉"],
  "学习": ["看书", "读书", "充电"]
}
```

## 📊 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/time/current` | GET | 获取当前任务 |
| `/api/time/report?period=today` | GET | 获取统计报表 |
| `/api/time/start?task=工作` | GET | 开始任务 |
| `/api/time/stop` | GET | 停止任务 |

## 🔧 运行环境

- Python 3.x
- Android (需Termux/Proot环境)
- Operit AI (可选，用于自动App检测)

## 📝 版本历史

详见 [CHANGELOG.md](docs/CHANGELOG.md)

## 📄 License

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Copyright (c) 2026 Moqim-Flourite

本项目采用 [MIT License](LICENSE) 开源。
