#!/usr/bin/env python3
"""
GPQA评测结果分析脚本
分析评测结果，生成统计报告
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_results(results_file):
    """分析评测结果"""
    
    print(f"Loading results from: {results_file}")
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    completed = data.get('completed', [])
    failed = data.get('failed', [])
    
    if not completed:
        print("No completed evaluations found!")
        return
    
    # 基础统计
    total = len(completed) + len(failed)
    success_count = len(completed)
    correct = sum(1 for r in completed if r.get('is_correct'))
    
    print("\n=== Basic Statistics ===")
    print(f"Total questions: {total}")
    print(f"Successfully evaluated: {success_count} ({success_count/total:.1%})")
    print(f"Failed (timeout/error): {len(failed)} ({len(failed)/total:.1%})")
    print(f"Correct answers: {correct}/{success_count} ({correct/success_count:.2%})")
    
    # 位置偏见分析
    print("\n=== Position Bias Analysis ===")
    position_stats = defaultdict(int)
    position_correct = defaultdict(int)
    
    for result in completed:
        if answer := result.get('model_answer'):
            position_stats[answer] += 1
            if result.get('is_correct'):
                position_correct[answer] += 1
    
    print("Answer distribution:")
    for letter in ['A', 'B', 'C', 'D']:
        count = position_stats[letter]
        pct = count / success_count if success_count > 0 else 0
        correct_count = position_correct[letter]
        accuracy = correct_count / count if count > 0 else 0
        print(f"  {letter}: {count:3d} ({pct:5.1%}) - Accuracy when chosen: {accuracy:.1%}")
    
    # 学科分析
    print("\n=== Subject Analysis ===")
    subject_stats = defaultdict(lambda: {'total': 0, 'correct': 0, 'failed': 0})
    
    for result in completed:
        subject = result.get('subject', 'Unknown')
        subject_stats[subject]['total'] += 1
        if result.get('is_correct'):
            subject_stats[subject]['correct'] += 1
    
    for result in failed:
        subject = result.get('subject', 'Unknown')
        subject_stats[subject]['total'] += 1
        subject_stats[subject]['failed'] += 1
    
    print("Performance by subject:")
    for subject, stats in sorted(subject_stats.items()):
        total = stats['total']
        correct = stats['correct']
        completed_subj = total - stats['failed']
        acc = correct / completed_subj if completed_subj > 0 else 0
        print(f"  {subject:20s}: {acc:5.1%} ({correct:2d}/{completed_subj:2d}) " +
              f"[Failed: {stats['failed']}]")
    
    # 时间分析
    print("\n=== Time Analysis ===")
    times = [r.get('elapsed_time', 0) for r in completed if r.get('elapsed_time')]
    if times:
        print(f"Average time per question: {sum(times)/len(times):.1f}s")
        print(f"Min time: {min(times):.1f}s")
        print(f"Max time: {max(times):.1f}s")
        print(f"Total time: {sum(times)/3600:.1f} hours")
    
    # Token使用分析
    print("\n=== Token Usage ===")
    tokens = [r.get('tokens_used', 0) for r in completed if r.get('tokens_used')]
    if tokens:
        print(f"Average tokens per question: {sum(tokens)/len(tokens):.0f}")
        print(f"Total tokens used: {sum(tokens):,}")
        print(f"Estimated cost: ${sum(tokens) * 0.00001:.2f} (assuming $0.01/1k tokens)")
    
    # 错误分析
    if failed:
        print("\n=== Failed Questions Analysis ===")
        error_types = defaultdict(int)
        for f in failed:
            error = f.get('error', 'Unknown error')
            error_types[error] += 1
        
        print("Error distribution:")
        for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {error}: {count}")
    
    # 生成可视化（如果需要）
    generate_visualizations(data)

def generate_visualizations(data):
    """生成结果可视化图表"""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        print("\nSkipping visualizations (matplotlib/seaborn not installed)")
        return
    
    completed = data.get('completed', [])
    if not completed:
        return
    
    # 设置样式
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 1. 答案分布
    ax = axes[0, 0]
    position_stats = defaultdict(int)
    for r in completed:
        if answer := r.get('model_answer'):
            position_stats[answer] += 1
    
    letters = ['A', 'B', 'C', 'D']
    counts = [position_stats[l] for l in letters]
    ax.bar(letters, counts)
    ax.set_title('Answer Distribution')
    ax.set_ylabel('Count')
    
    # 2. 学科表现
    ax = axes[0, 1]
    subject_acc = {}
    for r in completed:
        subject = r.get('subject', 'Unknown')
        if subject not in subject_acc:
            subject_acc[subject] = {'correct': 0, 'total': 0}
        subject_acc[subject]['total'] += 1
        if r.get('is_correct'):
            subject_acc[subject]['correct'] += 1
    
    subjects = list(subject_acc.keys())
    accuracies = [s['correct']/s['total'] for s in subject_acc.values()]
    ax.bar(range(len(subjects)), accuracies)
    ax.set_xticks(range(len(subjects)))
    ax.set_xticklabels(subjects, rotation=45, ha='right')
    ax.set_title('Accuracy by Subject')
    ax.set_ylabel('Accuracy')
    
    # 3. 时间分布
    ax = axes[1, 0]
    times = [r.get('elapsed_time', 0) for r in completed if r.get('elapsed_time')]
    if times:
        ax.hist(times, bins=30)
        ax.set_title('Response Time Distribution')
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Count')
    
    # 4. Token使用分布
    ax = axes[1, 1]
    tokens = [r.get('tokens_used', 0) for r in completed if r.get('tokens_used')]
    if tokens:
        ax.hist(tokens, bins=30)
        ax.set_title('Token Usage Distribution')
        ax.set_xlabel('Tokens')
        ax.set_ylabel('Count')
    
    plt.tight_layout()
    output_path = Path(results_file).parent / 'results_analysis.png'
    plt.savefig(output_path)
    print(f"\nVisualization saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="分析GPQA评测结果")
    parser.add_argument("results_file", help="结果文件路径")
    parser.add_argument("--viz", action="store_true", help="生成可视化图表")
    args = parser.parse_args()
    
    analyze_results(args.results_file)

if __name__ == "__main__":
    main()