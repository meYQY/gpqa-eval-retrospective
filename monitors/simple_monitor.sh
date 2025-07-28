#!/bin/bash
# 简单监控脚本 - 每5分钟报告进度

echo "=== 简单监控器启动 ==="
echo "开始时间: $(date)"
echo

while true; do
    echo "[$(date +%H:%M:%S)] 状态检查"
    
    # 检查进程
    if ps aux | grep -v grep | grep -q "python.*gpqa_test_resumable.py"; then
        echo "  ✓ 测试进程运行中"
        
        # 显示最新进度
        LATEST=$(tail -5 gpqa_*.log 2>/dev/null | grep "处理第" | tail -1)
        if [ -n "$LATEST" ]; then
            echo "  最新: $LATEST"
        fi
    else
        echo "  ❌ 测试进程未运行！"
        
        # 检查完成情况
        if [ -f gpqa_checkpoint.json ]; then
            COMPLETED=$(python3 -c "import json; print(len(json.load(open('gpqa_checkpoint.json')).get('completed_questions', [])))")
            echo "  已完成: $COMPLETED 题"
            
            if [ "$COMPLETED" -lt 150 ]; then
                echo "  重启测试..."
                python3 gpqa_test_resumable.py 150 > "gpqa_restart_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
                echo "  ✓ 已重启 (PID: $!)"
            fi
        fi
    fi
    
    echo
    sleep 300  # 5分钟
done