#!/usr/bin/env python3
"""
GPQA数据预处理脚本
将原始GPQA数据转换为评测所需的格式
"""

import json
import random
import argparse
from pathlib import Path
from datasets import load_dataset

def preprocess_gpqa_item(item, seed):
    """
    预处理单个GPQA题目
    1. 提取答案内容，去除标签
    2. 随机打乱顺序（使用固定seed保证可重复）
    3. 生成标准格式
    """
    # 收集所有答案
    answers = [
        item["Correct Answer"],
        item["Incorrect Answer 1"],
        item["Incorrect Answer 2"],
        item["Incorrect Answer 3"]
    ]
    
    # 记录正确答案
    correct_answer = item["Correct Answer"]
    
    # 使用问题ID或内容的hash作为seed，确保同一问题打乱顺序固定
    random.seed(seed)
    random.shuffle(answers)
    
    # 生成选项
    options = []
    correct_letter = None
    for i, answer in enumerate(answers):
        letter = chr(65 + i)  # A, B, C, D
        options.append(f"{letter}. {answer}")
        if answer == correct_answer:
            correct_letter = letter
    
    return {
        "id": item.get("id", hash(item["Question"])),
        "question": item["Question"],
        "options": "\n".join(options),
        "correct_answer": correct_letter,
        "subject": item.get("Subdomain", "Unknown"),
        "original_data": item  # 保留原始数据用于验证
    }

def main():
    parser = argparse.ArgumentParser(description="预处理GPQA数据集")
    parser.add_argument("--dataset", default="Idavidrein/gpqa", help="HuggingFace数据集名称")
    parser.add_argument("--subset", default="gpqa_main", help="数据子集")
    parser.add_argument("--output", default="data/gpqa_processed.json", help="输出文件路径")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    args = parser.parse_args()
    
    print(f"Loading dataset: {args.dataset}/{args.subset}")
    
    # 加载数据集
    # 注意：需要输入密码 deserted-untie-orchid
    dataset = load_dataset(args.dataset, args.subset)
    
    # 处理所有数据
    processed_data = []
    for idx, item in enumerate(dataset['train']):
        # 使用idx作为seed，确保每个问题的打乱是固定的
        processed_item = preprocess_gpqa_item(item, args.seed + idx)
        processed_data.append(processed_item)
        
        if (idx + 1) % 50 == 0:
            print(f"Processed {idx + 1} items...")
    
    # 保存处理后的数据
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessing complete!")
    print(f"Total items: {len(processed_data)}")
    print(f"Output saved to: {output_path}")
    
    # 验证数据格式
    print("\nSample processed item:")
    print(json.dumps(processed_data[0], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()