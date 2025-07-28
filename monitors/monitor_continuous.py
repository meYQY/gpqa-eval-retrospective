#!/usr/bin/env python3
"""
GPQA评测持续监控器
自动检测中断并发送告警
"""

import os
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path

class ContinuousMonitor:
    def __init__(self):
        self.checkpoint_file = Path("gpqa_checkpoint.json")
        self.log_dir = Path("gpqa_logs")
        self.last_checkpoint_update = None
        self.last_completed = 0
        self.no_progress_count = 0
        self.max_no_progress = 10  # 10次检查无进展则告警
        
    def get_latest_log(self):
        """获取最新的日志文件"""
        log_files = list(self.log_dir.glob("gpqa_test_*.log"))
        if not log_files:
            return None
        return max(log_files, key=lambda x: x.stat().st_mtime)
        
    def check_process(self):
        """检查进程是否运行"""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            return 'gpqa_test_resumable.py' in result.stdout
        except:
            return False
            
    def read_checkpoint(self):
        """读取检查点"""
        try:
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        except:
            return None
            
    def analyze_progress(self):
        """分析进度"""
        checkpoint = self.read_checkpoint()
        if not checkpoint:
            return None
            
        completed = len(checkpoint.get('completed_questions', []))
        last_saved = checkpoint.get('last_saved', '')
        
        # 检查是否有新进展
        has_progress = False
        if completed > self.last_completed:
            has_progress = True
            self.last_completed = completed
            self.no_progress_count = 0
        else:
            self.no_progress_count += 1
            
        return {
            'completed': completed,
            'total': 150,
            'last_saved': last_saved,
            'has_progress': has_progress,
            'errors': sum(1 for r in checkpoint.get('results', []) if 'error' in r)
        }
        
    def restart_if_needed(self):
        """必要时重启进程"""
        if not self.check_process() and self.no_progress_count > 2:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 检测到进程停止，尝试重启...")
            subprocess.run(['nohup', 'python3', 'gpqa_test_resumable.py', '>', 
                          f'gpqa_restart_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', 
                          '2>&1', '&'], shell=True)
            time.sleep(5)
            return True
        return False
        
    def run(self):
        """主监控循环"""
        print("=== GPQA 持续监控器启动 ===")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        while True:
            try:
                # 检查进程
                process_running = self.check_process()
                
                # 分析进度
                progress = self.analyze_progress()
                
                # 获取最新日志
                latest_log = self.get_latest_log()
                
                # 打印状态
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 监控状态")
                print("-" * 40)
                
                if process_running:
                    print("✅ 进程运行中")
                else:
                    print("❌ 进程未检测到")
                    
                if progress:
                    print(f"📊 进度: {progress['completed']}/{progress['total']} " +
                          f"({'%.1f' % (progress['completed']/progress['total']*100)}%)")
                    print(f"   错误: {progress['errors']}")
                    
                    if progress['has_progress']:
                        print("   ✅ 有新进展")
                    else:
                        print(f"   ⚠️  无进展 (连续{self.no_progress_count}次)")
                        
                if latest_log:
                    # 读取日志最后几行
                    with open(latest_log, 'r') as f:
                        lines = f.readlines()
                        last_lines = lines[-5:] if len(lines) > 5 else lines
                        
                    print(f"\n📄 最新日志 ({latest_log.name}):")
                    for line in last_lines:
                        if line.strip():
                            print(f"   {line.strip()[:80]}...")
                            
                # 检查是否需要重启
                if self.no_progress_count >= self.max_no_progress:
                    print(f"\n🚨 警告: 已经{self.no_progress_count}次检查无进展!")
                    if self.restart_if_needed():
                        print("   已尝试重启进程")
                        self.no_progress_count = 0
                        
                # 检查是否完成
                if progress and progress['completed'] >= 150:
                    print("\n🎉 评测已完成!")
                    break
                    
                # 等待60秒
                time.sleep(60)
                
            except KeyboardInterrupt:
                print("\n\n监控器已停止")
                break
            except Exception as e:
                print(f"\n错误: {e}")
                time.sleep(60)

if __name__ == "__main__":
    monitor = ContinuousMonitor()
    monitor.run()