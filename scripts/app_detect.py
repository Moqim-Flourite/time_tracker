#!/usr/bin/env python3
"""
App检测脚本 - 获取当前使用的App并推断活动
使用方法：
  python3 app_detect.py status          # 查看当前任务状态
  python3 app_detect.py detect <包名>   # 检测指定App并自动切换
  python3 app_detect.py screen          # 检测屏幕状态（熄屏/亮屏）
  python3 app_detect.py switch <类别>   # 手动切换任务
  python3 app_detect.py mappings        # 查看App映射配置
  python3 app_detect.py assistants      # 查看辅助应用白名单

辅助应用白名单说明：
  当正在进行某项活动时，打开白名单中的应用不会触发状态切换。
  例如：正在"睡觉"时打开宝可梦睡眠/网易云音乐/哔哩哔哩 → 保持"睡觉"状态

注意：此脚本本身无法获取前台App，需要外部传入包名。
      Operit AI会在每次交互时调用此脚本并传入当前App信息。
"""

import sys
import os
import json
from datetime import datetime, timedelta
import subprocess
import re

BASE_DIR = "/home/operit"
LOG_FILE = os.path.join(BASE_DIR, "time_log.csv")
CURRENT_TASK_FILE = os.path.join(BASE_DIR, "current_task.json")
APP_LOG_FILE = os.path.join(BASE_DIR, "app_usage_log.json")

# 辅助应用白名单 - 当正在进行某活动时，打开这些应用不会触发切换
# 格式: {当前活动类别: [允许打开的应用包名列表]}
# 说明: 这些应用是"辅助"当前活动的，不应触发状态切换
ASSISTANT_APPS = {
    "睡觉": [
        "jp.pokemon.pokemonsleep",  # 宝可梦睡眠 - 睡眠追踪
        "com.netease.cloudmusic",  # 网易云音乐 - 听歌睡觉
        "com.kugou.android",  # 酷狗音乐
        "com.kuwo.player",  # 酷我音乐
        "tv.danmaku.bili",  # 哔哩哔哩 - 放海浪声等助眠音频
        "com.bilibili.app.in",  # B站国际版
        "com.mi.health",  # 小米健康 - 睡眠监测
        "com.huawei.health",  # 华为健康 - 睡眠监测
    ],
    "学习": [
        "com.eusoft.eudic",  # 欧路词典 - 查单词
        "com.eusoft.ting.en",  # 每日英语听力
        "com.duolingo",  # 多邻国
        "com.shici",  # 诗词
        "com.bf.words_recite",  # 背单词
    ],
    "工作": [
        "com.tencent.androidqqmail",  # QQ邮箱 - 查邮件
        "com.google.android.apps.docs.editors.sheets",  # Google表格
        "com.google.android.apps.docs.editors.slides",  # Google幻灯片
        "com.google.android.apps.docs.editors.docs",  # Google文档
        "cn.wps.moffice_eng.xiaomi.lite",  # WPS
        "cn.wps.note",  # WPS笔记
    ],
}

# App包名映射（类别）- 按使用频率和分类整理
APP_MAPPINGS = {
    # ========== 社交类 -> 刷手机 ==========
    "com.tencent.mm": "刷手机",  # 微信
    "com.tencent.mobileqq": "刷手机",  # QQ
    "com.sina.weibo": "刷手机",  # 微博
    "com.xingin.xhs": "刷手机",  # 小红书
    "com.ss.android.ugc.aweme": "刷手机",  # 抖音
    "com.smile.gifmaker": "刷手机",  # 快手
    "org.telegram.messenger": "刷手机",  # Telegram
    "com.tencent.karaoke": "刷手机",  # 全民K歌
    
    # ========== 视频类 -> 刷手机 ==========
    "tv.danmaku.bili": "刷手机",  # B站（国内版）
    "com.bilibili.app.in": "刷手机",  # B站（国际版）
    "com.youku.phone": "刷手机",  # 优酷
    "com.qiyi.video": "刷手机",  # 爱奇艺
    "com.baidu.youavideo": "刷手机",  # 百度视频
    "com.miui.video": "刷手机",  # 小米视频
    "com.google.android.youtube": "刷手机",  # YouTube
    
    # ========== 阅读/小说类 -> 刷手机 ==========
    "io.legado.app.release": "刷手机",  # 阅读
    "com.dragon.read": "刷手机",  # 番茄小说
    "com.tencent.weread": "刷手机",  # 微信读书
    "com.duokan.reader": "刷手机",  # 多看阅读
    
    # ========== 音乐类 -> 刷手机 ==========
    "com.netease.cloudmusic": "刷手机",  # 网易云音乐
    "com.kugou.android": "刷手机",  # 酷狗音乐
    "com.kuwo.player": "刷手机",  # 酷我音乐
    "com.tencent.qqmusic": "刷手机",  # QQ音乐
    
    # ========== 游戏类 -> 打游戏 ==========
    "com.tencent.tmgp.sgame": "打游戏",  # 王者荣耀
    "com.tencent.tmgp.sgamece": "打游戏",  # 王者荣耀CE
    "com.miHoYo.Yuanshen": "打游戏",  # 原神
    "jp.pokemon.pokemonsleep": "打游戏",  # 宝可梦睡眠
    "com.hypergryph.endfield.bilibili": "打游戏",  # 明日方舟：终末地
    "com.nianticproject.ingress": "打游戏",  # Ingress
    "com.threeminutegames.lifeline.google": "打游戏",  # Lifeline
    "com.prineside.tdi2": "打游戏",  # 王国保卫战
    
    # ========== AI工具类 ==========
    "com.ai.assistance.operit": "调ai",  # Operit AI
    "com.openai.chatgpt": "调ai",  # ChatGPT
    "com.google.android.apps.bard": "调ai",  # Gemini
    "com.tencent.hunyuan.app.chat": "调ai",  # 腾讯混元
    "com.crirp.zhipu": "调ai",  # 智谱清言
    "com.larus.nova": "调ai",  # 豆包
    "com.ailian.hope": "刷手机",  # 希望清单
    
    # ========== 工作类 -> 工作 ==========
    "com.tencent.wemeet.app": "工作",  # 腾讯会议
    "com.alibaba.android.rimet": "工作",  # 钉钉
    "com.ss.android.lark": "工作",  # 飞书
    "com.tencent.androidqqmail": "工作",  # QQ邮箱
    "com.google.android.apps.docs.editors.sheets": "工作",  # Google表格
    "com.google.android.apps.docs.editors.slides": "工作",  # Google幻灯片
    "com.google.android.apps.docs.editors.docs": "工作",  # Google文档
    "cn.wps.moffice_eng.xiaomi.lite": "工作",  # WPS
    "cn.wps.note": "工作",  # WPS笔记
    
    # ========== 购物类 -> 刷手机 ==========
    "com.taobao.taobao": "刷手机",  # 淘宝
    "com.jingdong.app.mall": "刷手机",  # 京东
    "com.xunmeng.pinduoduo": "刷手机",  # 拼多多
    "com.taobao.idlefish": "刷手机",  # 闲鱼
    "com.sankuai.meituan": "刷手机",  # 美团
    
    # ========== 出行/导航 -> 交通 ==========
    "com.autonavi.minimap": "交通",  # 高德地图
    "com.umetrip.android.msky.app": "交通",
    "com.cmi.jegotrip": "交通",  # 航旅纵横
    "com.baidu.carlife.vivo": "交通",  # 百度CarLife
    
    # ========== 学习类 -> 学习 ==========
    "com.eusoft.eudic": "学习",  # 欧路词典
    "com.eusoft.ting.en": "学习",  # 每日英语听力
    "com.duolingo": "学习",  # 多邻国
    "com.shici": "学习",  # 诗词
    "com.bf.words_recite": "学习",  # 背单词
    
    # ========== 生活服务（忽略或特定） ==========
    "com.eg.android.AlipayGphone": None,  # 支付宝（忽略）
    "cn.gov.pbc.dcep": None,  # 数字人民币（忽略）
    "cmb.pb": None,  # 招商银行（忽略）
    "com.cmbchina.ccd.pluto.cmbActivity": None,  # 掌上生活（忽略）
    "com.xiaomi.smarthome": None,  # 米家（忽略）
    "com.duokan.phone.remotecontroller": None,  # 万能遥控（忽略）
    "com.mi.health": None,  # 小米运动健康（忽略）
    "com.huawei.health": None,  # 华为健康（忽略）
    "com.midea.ai.appliances": None,  # 美的（忽略）
    
    # ========== 系统类（忽略） ==========
    "com.miui.home": None,  # 桌面
    "com.android.launcher": None,  # 桌面
    "com.android.systemui": None,  # 系统界面
    "com.android.settings": None,  # 设置
    "com.android.camera": None,  # 相机
    "com.miui.gallery": None,  # 相册
    "com.miui.securitycenter": None,  # 手机管家
    "com.miui.mediaeditor": None,  # 小米编辑
    "com.miui.calculator": None,  # 计算器
    "com.miui.notes": None,  # 笔记
    "com.android.deskclock": None,  # 时钟
    "com.miui.compass": None,  # 指南针
    "com.arashivision.insta360akiko": "工作",  # Insta360相机
    "com.arashivision.instacam": "工作",  # Insta360
    "com.miui.screenrecorder": None,  # 录屏
    "com.android.soundrecorder": None,  # 录音机
    
    # ========== 视频/内容创作 -> 工作 ==========
    "com.lemon.lv": "工作",  # 剪映
    "com.bilibili.studio": "工作",  # 必剪
    "com.duapps.recorder": "工作",  # 录屏大师
    "cn.wps.moffice_eng.xiaomi.lite": "工作",  # WPS
    
    # ========== 应用商店（忽略） ==========
    "com.xiaomi.market": None,  # 小米应用商店
    "com.android.vending": None,  # Google Play
    "com.coolapk.market": None,  # 酷安
}

# App友好名称映射（用于备注）
APP_NAMES = {
    # 社交类
    "com.arashivision.insta360akiko": "Insta360相机",
    "com.tencent.mm": "微信",
    "com.tencent.mobileqq": "QQ",
    "com.sina.weibo": "微博",
    "com.xingin.xhs": "小红书",
    "com.ss.android.ugc.aweme": "抖音",
    "com.smile.gifmaker": "快手",
    "org.telegram.messenger": "Telegram",
    "com.tencent.karaoke": "全民K歌",
    
    # 视频类
    "tv.danmaku.bili": "B站",
    "com.bilibili.app.in": "B站国际版",
    "com.youku.phone": "优酷",
    "com.qiyi.video": "爱奇艺",
    "com.baidu.youavideo": "百度视频",
    "com.miui.video": "小米视频",
    "com.google.android.youtube": "YouTube",
    
# 阅读/小说类
    "io.legado.app.release": "阅读",
    "com.dragon.read": "番茄小说",
    "com.tencent.weread": "微信读书",
    "com.duokan.reader": "多看阅读",
    
    # 音乐类
    "com.netease.cloudmusic": "网易云音乐",
    "com.kugou.android": "酷狗音乐",
    "com.kuwo.player": "酷我音乐",
    "com.tencent.qqmusic": "QQ音乐",
    
    # 游戏类
    "com.tencent.tmgp.sgame": "王者荣耀",
    "com.tencent.tmgp.sgamece": "王者荣耀CE",
    "com.miHoYo.Yuanshen": "原神",
    "jp.pokemon.pokemonsleep": "宝可梦睡眠",
    "com.hypergryph.endfield.bilibili": "明日方舟终末地",
    "com.nianticproject.ingress": "Ingress",
    "com.threeminutegames.lifeline.google": "Lifeline",
    "com.prineside.tdi2": "王国保卫战",
    
    # AI工具类
    "com.ai.assistance.operit": "Operit",
    "com.openai.chatgpt": "ChatGPT",
    "com.google.android.apps.bard": "Gemini",
    "com.tencent.hunyuan.app.chat": "元宝",
    "com.crirp.zhipu": "智谱清言",
    "com.larus.nova": "豆包",
    
    # 希望清单
    "com.ailian.hope": "希望清单",
    
    # 工作类
    "com.tencent.wemeet.app": "腾讯会议",
    "com.alibaba.android.rimet": "钉钉",
    "com.ss.android.lark": "飞书",
    "com.tencent.androidqqmail": "QQ邮箱",
    "com.google.android.apps.docs.editors.sheets": "Google表格",
    "com.google.android.apps.docs.editors.slides": "Google幻灯片",
    "com.google.android.apps.docs.editors.docs": "Google文档",
    "cn.wps.moffice_eng.xiaomi.lite": "WPS",
    "cn.wps.note": "WPS笔记",
    
    # 购物类
    "com.taobao.taobao": "淘宝",
    "com.jingdong.app.mall": "京东",
    "com.xunmeng.pinduoduo": "拼多多",
    "com.taobao.idlefish": "闲鱼",
    "com.sankuai.meituan": "美团",
    
    # 出行/导航
    "com.autonavi.minimap": "高德地图",
    "com.umetrip.android.msky.app": "航旅纵横",
    "com.baidu.carlife.vivo": "百度CarLife",
    "com.cmi.jegotrip": "交通",  # 捷旅旅行
    
    # 学习类
    "com.eusoft.eudic": "欧路词典",
    "com.eusoft.ting.en": "每日英语听力",
    "com.duolingo": "多邻国",
    "com.shici": "诗词",
    "com.bf.words_recite": "背单词",
    
    # 生活服务
    "com.eg.android.AlipayGphone": "支付宝",
    "cn.gov.pbc.dcep": "数字人民币",
    "cmb.pb": "招商银行",
    "com.cmbchina.ccd.pluto.cmbActivity": "掌上生活",
    "com.xiaomi.smarthome": "米家",
    "com.duokan.phone.remotecontroller": "万能遥控",
    "com.mi.health": "小米运动健康",
    "com.huawei.health": "华为健康",
"com.midea.ai.appliances": "美的",
    
    # 视频/内容创作
    "com.lemon.lv": "剪映",
    "com.bilibili.studio": "必剪",
    "com.duapps.recorder": "录屏大师",
    
    # 应用商店
    "com.xiaomi.market": "小米应用商店",
    "com.android.vending": "Google Play",
    "com.coolapk.market": "酷安",
}

# 检测配置
MIN_SWITCH_INTERVAL = 15  # 最小切换间隔（秒）- 从配置文件读取，默认15秒
SCREEN_OFF_CATEGORY = "空闲"  # 熄屏/锁屏时的任务类别

# 尝试从配置文件读取切换间隔
def load_switch_interval():
    """从配置文件加载切换间隔"""
    config_file = os.path.join(BASE_DIR, "app_monitor_config.json")
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get("min_switch_interval", 15)
    except:
        pass
    return 15

MIN_SWITCH_INTERVAL = load_switch_interval()
IGNORE_PACKAGES = {  # 忽略的包名（不触发切换）
    # 注意：com.ai.assistance.operit 不忽略，因为打开Operit = 调ai
    # 系统类App在APP_MAPPINGS中设为None即可忽略
}


def get_screen_state():
    """
    检测屏幕状态
    返回: (is_screen_on, 状态描述)
    """
    try:
        # 尝试使用 adb 连接本地设备执行 dumpsys
        result = subprocess.run(
            ['adb', 'shell', 'dumpsys', 'display'],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        
        # 查找 mScreenState
        match = re.search(r'mScreenState=(\w+)', output)
        if match:
            state = match.group(1)
            is_on = state.upper() in ['ON', 'ON_BUT_DIM']
            return is_on, f"屏幕状态: {state}"
        
        return True, "无法检测屏幕状态，默认亮屏"
    except Exception as e:
        # adb 不可用，检查屏幕状态文件
        screen_state_file = os.path.join(BASE_DIR, "screen_state.json")
        if os.path.exists(screen_state_file):
            try:
                with open(screen_state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    is_on = data.get('screen_on', True)
                    return is_on, f"屏幕状态(缓存): {'亮屏' if is_on else '熄屏'}"
            except:
                pass
        
        return True, f"检测屏幕状态失败: {e}"


def get_current_task():
    """获取当前正在进行的任务"""
    if os.path.exists(CURRENT_TASK_FILE):
        with open(CURRENT_TASK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def get_app_category(package_name):
    """
    根据App包名推断活动类别
    返回: (类别, 置信度, 说明)
    """
    if package_name in APP_MAPPINGS:
        category = APP_MAPPINGS[package_name]
        if category:
            return (category, 0.95, f"App映射: {package_name}")
        else:
            return (None, 0, f"App忽略: {package_name}")
    
    # 模糊匹配
    for pkg, category in APP_MAPPINGS.items():
        if category and (pkg in package_name or package_name in pkg):
            return (category, 0.7, f"模糊匹配: {package_name} -> {pkg}")
    
    return (None, 0, f"未知App: {package_name}")


def should_switch_app(new_category, package_name, current_task):
    """
    判断是否应该根据App切换任务
    """
    # 忽略特定包名
    if package_name in IGNORE_PACKAGES:
        return False, "忽略包名（Operit AI）"
    
    # 没有检测到类别
    if not new_category:
        return False, "未识别App类别"
    
    # 当前无任务
    if not current_task:
        return True, "当前无任务"
    
    current_category = current_task.get('task_name', '')
    
    # 类别相同，不切换
    if new_category == current_category:
        return False, f"类别相同 ({new_category})"
    
    # 检查辅助应用白名单
    if current_category in ASSISTANT_APPS:
        assistant_list = ASSISTANT_APPS[current_category]
        if package_name in assistant_list:
            return False, f"辅助应用白名单（{current_category}时使用{APP_NAMES.get(package_name, package_name)}）"
    
    # 检查时间间隔
    try:
        start_time_str = current_task.get('start_time', '')
        # 支持多种时间格式
        for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
            try:
                start_time = datetime.strptime(start_time_str, fmt)
                break
            except:
                continue
        else:
            return True, f"检测到新活动: {new_category}"
        
        # 转换为北京时间（如果需要）
        from datetime import timezone, timedelta
        BEIJING_TZ = timezone(timedelta(hours=8))
        
        elapsed = (datetime.now(BEIJING_TZ) - start_time).total_seconds()
        if elapsed < MIN_SWITCH_INTERVAL:
            return False, f"切换间隔过短 ({int(elapsed)}s < {MIN_SWITCH_INTERVAL}s)"
    except Exception as e:
        pass
    
    return True, f"检测到App切换: {new_category}"


def log_app_usage(package_name, category, action):
    """记录App使用日志"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "package": package_name,
        "category": category,
        "action": action
    }
    
    logs = []
    if os.path.exists(APP_LOG_FILE):
        with open(APP_LOG_FILE, 'r', encoding='utf-8') as f:
            try:
                logs = json.load(f)
            except:
                logs = []
    
    logs.append(log_entry)
    
    # 只保留最近500条记录
    if len(logs) > 500:
        logs = logs[-500:]
    
    with open(APP_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def detect_and_switch(package_name, auto_switch=True):
    """
    检测App并决定是否切换任务
    返回检测结果字典
    """
    category, confidence, detail = get_app_category(package_name)
    current_task = get_current_task()
    
    # 获取App友好名称（用于备注）
    app_name = APP_NAMES.get(package_name, package_name.split('.')[-1] if package_name else "")
    
    result = {
        "package": package_name,
        "app_name": app_name,
        "detected": category,
        "confidence": confidence,
        "detail": detail,
        "switched": False,
        "reason": ""
    }
    
    if category and auto_switch:
        should_switch, reason = should_switch_app(category, package_name, current_task)
        result["reason"] = reason
        
        if should_switch:
            # 执行切换（带App名称备注）
            cmd = ['python3', os.path.join(BASE_DIR, 'start_task.py'), category]
            if app_name:
                cmd.append(app_name)  # 添加备注参数
            switch_result = subprocess.run(cmd, capture_output=True, text=True)
            result["switched"] = True
            result["switch_output"] = switch_result.stdout
    else:
        result["reason"] = "未检测到活动" if not category else "自动切换已禁用"
    
    # 记录日志
    log_app_usage(package_name, category, "switched" if result["switched"] else "detected")
    
    return result


def detect_with_screen(package_name=None, auto_switch=True):
    """
    先检测屏幕状态，再决定是否切换任务
    熄屏时切换到"熄屏"任务
    锁屏时切换到"熄屏"任务（用户不在使用手机）
    亮屏时按App映射切换
    返回检测结果字典
    """
    current_task = get_current_task()
    
    # 如果已经收到 SCREEN_OFF 或 SCREEN_LOCKED 信号，直接信任它
    # Android 监控脚本已经通过 dumpsys 正确检测了屏幕状态
    if package_name == "SCREEN_OFF":
        is_screen_on = False
        is_locked = False
        screen_desc = "屏幕已熄灭（来自Android监控）"
    elif package_name == "SCREEN_LOCKED":
        is_screen_on = True  # 屏幕亮着
        is_locked = True
        screen_desc = "屏幕已锁屏（来自Android监控）"
    else:
        is_screen_on, screen_desc = get_screen_state()
        is_locked = False
    
    result = {
        "screen_on": is_screen_on,
        "is_locked": is_locked,
        "screen_desc": screen_desc,
        "package": package_name,
        "app_name": "",
        "detected": None,
        "confidence": 0,
        "detail": "",
        "switched": False,
        "reason": ""
    }
    
    # 熄屏或锁屏状态都应该切换到"熄屏"任务
    if not is_screen_on or is_locked:
        # 熄屏或锁屏状态
        result["detected"] = SCREEN_OFF_CATEGORY
        result["confidence"] = 1.0
        result["detail"] = "锁屏" if is_locked else "屏幕已熄灭"
        
        # 检查是否需要切换到熄屏任务
        current_category = current_task.get('task_name', '') if current_task else ''
        if current_category != SCREEN_OFF_CATEGORY:
            should_switch, reason = should_switch_app(SCREEN_OFF_CATEGORY, "screen_off", current_task)
            result["reason"] = reason
            
            if should_switch and auto_switch:
                switch_result = subprocess.run(
                    ['python3', os.path.join(BASE_DIR, 'start_task.py'), SCREEN_OFF_CATEGORY],
                    capture_output=True, text=True
                )
                result["switched"] = True
                result["switch_output"] = switch_result.stdout
                log_app_usage("screen_locked" if is_locked else "screen_off", SCREEN_OFF_CATEGORY, "switched")
            else:
                log_app_usage("screen_locked" if is_locked else "screen_off", SCREEN_OFF_CATEGORY, "detected")
        else:
            result["reason"] = f"已经是{SCREEN_OFF_CATEGORY}状态"
    else:
        # 亮屏且未锁屏，按App检测
        if package_name:
            app_result = detect_and_switch(package_name, auto_switch)
            result.update(app_result)
        else:
            result["detail"] = "屏幕亮起，等待App信息"
            result["reason"] = "需要传入App包名"
    
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n当前App映射配置：")
        for pkg, cat in sorted(APP_MAPPINGS.items()):
            if cat:
                print(f"  {pkg} → {cat}")
        return
    
    command = sys.argv[1]
    
    if command == 'status':
        current = get_current_task()
        if current:
            print(f"当前任务: {current.get('task_name')}")
            print(f"开始时间: {current.get('start_time')}")
            print(f"运行状态: {'运行中' if current.get('running') else '已停止'}")
        else:
            print("当前无任务")
    
    elif command == 'screen':
        # 检测屏幕状态
        is_on, desc = get_screen_state()
        print(f"📺 {desc}")
        print(f"状态: {'亮屏' if is_on else '熄屏'}")
        
        # 如果熄屏，切换到熄屏任务
        if not is_on:
            result = detect_with_screen(auto_switch=True)
            if result['switched']:
                print(f"✅ 已切换到「{SCREEN_OFF_CATEGORY}」任务")
            else:
                print(f"⏭️ 未切换: {result['reason']}")
    
    elif command == 'detect' and len(sys.argv) >= 3:
        package_name = sys.argv[2]
        # 使用带熄屏检测的版本
        result = detect_with_screen(package_name, auto_switch=True)
        
        print(f"📺 {result['screen_desc']}")
        print(f"📱 App: {package_name}")
        print(f"🔍 检测类别: {result['detected'] or '未知'}")
        print(f"📊 置信度: {result['confidence']:.0%}")
        print(f"📋 详情: {result['detail']}")
        if result['switched']:
            print("✅ 已自动切换任务")
        else:
            print(f"⏭️ 未切换: {result['reason']}")
    
    elif command == 'switch' and len(sys.argv) >= 3:
        category = sys.argv[2]
        subprocess.run(['python3', os.path.join(BASE_DIR, 'start_task.py'), category])
    
    elif command == 'mappings':
        print("App包名映射：")
        for pkg, cat in sorted(APP_MAPPINGS.items()):
            if cat:
                print(f"  {pkg} → {cat}")
    
    elif command == 'assistants':
        print("📋 辅助应用白名单（不触发状态切换）：")
        for category, packages in ASSISTANT_APPS.items():
            print(f"\n【{category}】")
            for pkg in packages:
                app_name = APP_NAMES.get(pkg, pkg.split('.')[-1])
                print(f"  • {app_name} ({pkg})")
    
    else:
        print(__doc__)


if __name__ == "__main__":
    main()