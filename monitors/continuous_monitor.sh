#!/bin/bash
# 持续监控脚本 - 每5分钟检查一次进程状态

echo "=== 持续监控器启动 ==="
echo "开始时间: $(date)"
echo "监控间隔: 5分钟"
echo

while true; do
    echo "[$(date +%H:%M:%S)] 检查测试状态..."
    
    # 检查是否有测试进程在运行
    TEST_PID=$(ps aux | grep -E "python.*gpqa_test_resumable.py" | grep -v grep | awk '{print $2}' | head -1)
    
    if [ -n "$TEST_PID" ]; then
        echo "  测试进程运行中 (PID: $TEST_PID)"
        
        # 检查最新日志文件
        LATEST_LOG=$(ls -t gpqa_*.log 2>/dev/null | head -1)
        if [ -n "$LATEST_LOG" ]; then
            # 获取文件大小和最后修改时间
            if [[ "$OSTYPE" == "darwin"* ]]; then
                FILE_SIZE=$(stat -f%z "$LATEST_LOG")
                LAST_MOD=$(stat -f %m "$LATEST_LOG")
            else
                FILE_SIZE=$(stat -c%s "$LATEST_LOG")
                LAST_MOD=$(stat -c %Y "$LATEST_LOG")
            fi
            
            CURRENT_TIME=$(date +%s)
            TIME_DIFF=$((CURRENT_TIME - LAST_MOD))
            
            echo "  日志文件: $LATEST_LOG"
            echo "  文件大小: $FILE_SIZE bytes"
            echo "  最后更新: ${TIME_DIFF}秒前"
            
            # 显示最新进度
            LAST_PROGRESS=$(tail -20 "$LATEST_LOG" | grep "处理第" | tail -1)
            if [ -n "$LAST_PROGRESS" ]; then
                echo "  最新进度: $LAST_PROGRESS"
            fi
            
            # 如果超过15分钟没更新，认为进程卡住
            if [ $TIME_DIFF -gt 900 ]; then
                echo "  ⚠️  警告：进程可能卡住了（15分钟无更新）"
                echo "  终止卡住的进程..."
                kill -9 $TEST_PID
                sleep 2
                
                echo "  重新启动测试..."
                python3 gpqa_test_resumable.py 150 > "gpqa_recovery_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
                NEW_PID=$!
                echo "  ✓ 已重启测试 (新PID: $NEW_PID)"
            fi
        fi
    else
        echo "  ❌ 没有检测到运行的测试进程！"
        
        # 检查是否已完成
        if [ -f gpqa_checkpoint.json ]; then
            COMPLETED=$(python3 -c "import json; data=json.load(open('gpqa_checkpoint.json')); print(len(data.get('completed_questions', [])))")
            echo "  已完成: $COMPLETED 题"
            
            if [ "$COMPLETED" -lt 150 ]; then
                echo "  重启测试以继续..."
                python3 gpqa_test_resumable.py 150 > "gpqa_recovery_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
                NEW_PID=$!
                echo "  ✓ 已重启测试 (PID: $NEW_PID)"
            fi
        else
            echo "  启动新的测试..."
            python3 gpqa_test_resumable.py 150 > "gpqa_new_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
            NEW_PID=$!
            echo "  ✓ 已启动测试 (PID: $NEW_PID)"
        fi
    fi
    
    echo
    sleep 300  # 5分钟
done