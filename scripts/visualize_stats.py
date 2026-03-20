import json
import csv
import datetime
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端

BASE_DIR = os.path.expanduser("~")
LOG_FILE = os.path.join(BASE_DIR, "time_log.csv")

def generate_pie_chart(period="today"):
    """生成时间分布饼图"""
    if not os.path.exists(LOG_FILE):
        return None, "目前还没有任何记录数据。"
    
    stats = {}
    now = datetime.datetime.now()
    
    with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            start_dt = datetime.datetime.strptime(row['开始时间'], "%Y-%m-%d %H:%M:%S")
            
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
        return None, f"在 {period} 范围内没有找到记录。"

    # 准备绘图数据
    labels = list(stats.keys())
    sizes = list(stats.values())
    total_sec = sum(sizes)
    
    # 计算百分比
    percentages = [(size / total_sec) * 100 for size in sizes]
    
    # 过滤掉小于1%的项目
    filtered_labels = []
    filtered_sizes = []
    filtered_percentages = []
    
    for i, (label, size, percent) in enumerate(zip(labels, sizes, percentages)):
        if percent >= 1:
            filtered_labels.append(label)
            filtered_sizes.append(size)
            filtered_percentages.append(percent)
    
    # 创建饼图
    plt.figure(figsize=(10, 8))
    colors = plt.cm.Set3(range(len(filtered_labels)))
    
    wedges, texts, autotexts = plt.pie(
        filtered_sizes, 
        labels=filtered_labels, 
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        explode=[0.05] * len(filtered_labels)
    )
    
    # 美化图表
    plt.title(f'时间分布饼图 ({period})', fontsize=16, fontweight='bold')
    plt.axis('equal')
    
    # 添加图例
    legend_labels = [f'{label}: {sec//3600}h {(sec%3600)//60}m ({percent:.1f}%)' 
                    for label, sec, percent in zip(filtered_labels, filtered_sizes, filtered_percentages)]
    plt.legend(wedges, legend_labels, title="时间详情", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    
    # 保存图片
    chart_path = os.path.join(BASE_DIR, f"time_chart_{period}.png")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return chart_path, f"已生成饼图：{chart_path}"

def generate_bar_chart(period="today"):
    """生成时间分布柱状图"""
    if not os.path.exists(LOG_FILE):
        return None, "目前还没有任何记录数据。"
    
    stats = {}
    now = datetime.datetime.now()
    
    with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            start_dt = datetime.datetime.strptime(row['开始时间'], "%Y-%m-%d %H:%M:%S")
            
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
        return None, f"在 {period} 范围内没有找到记录。"

    # 准备绘图数据
    labels = list(stats.keys())
    sizes = list(stats.values())
    
    # 转换为小时
    hours = [sec / 3600 for sec in sizes]
    
    # 创建柱状图
    plt.figure(figsize=(12, 8))
    bars = plt.bar(labels, hours, color=plt.cm.Set3(range(len(labels))))
    
    # 添加数值标签
    for bar, hour in zip(bars, hours):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{hour:.1f}h', ha='center', va='bottom')
    
    # 美化图表
    plt.title(f'时间分布柱状图 ({period})', fontsize=16, fontweight='bold')
    plt.xlabel('任务类别', fontsize=12)
    plt.ylabel('时长 (小时)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    # 保存图片
    chart_path = os.path.join(BASE_DIR, f"time_bar_chart_{period}.png")
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return chart_path, f"已生成柱状图：{chart_path}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        chart_type = sys.argv[1]
        period = sys.argv[2] if len(sys.argv) > 2 else "today"
        
        if chart_type == "pie":
            chart_path, message = generate_pie_chart(period)
        elif chart_type == "bar":
            chart_path, message = generate_bar_chart(period)
        else:
            print("支持的图表类型：pie, bar")
            sys.exit(1)
        
        if chart_path:
            print(message)
            print(f"图表已保存到：{chart_path}")
        else:
            print(message)