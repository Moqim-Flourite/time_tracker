#!/bin/bash
# 通知发送脚本 - 通过Shizuku发送Android通知
TITLE="$1"
CONTENT="$2"

if [ -z "$TITLE" ] || [ -z "$CONTENT" ]; then
    echo "用法: $0 <标题> <内容>"
    exit 1
fi

# 通过Shizuku的shell执行cmd命令
# 这个脚本需要被AI通过shell工具调用
cmd notification post -t "$TITLE" app_monitor "$CONTENT"
