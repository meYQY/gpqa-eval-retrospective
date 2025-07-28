#!/usr/bin/env python3
"""
简单直接的GPQA测试，不使用DeepEval框架
"""

import os
import json
import time
from dotenv import load_dotenv
from datasets import load_dataset
import requests
import random

# 加载环境变量
load_dotenv()

def call_grok_api(prompt: str, max_retries: int = 3):
    """直接调用Grok API"""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("未设置 XAI_API_KEY")
    
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "grok-4",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 100000  # 设置很大的token限制
    }
    
    # 设置代理
    proxies = {}
    if os.environ.get('https_proxy'):
        proxies = {
            'http': os.environ.get('http_proxy', ''),
            'https': os.environ.get('https_proxy', '')
        }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url, 
                headers=headers, 
                json=data, 
                timeout=600,  # 增加到10分钟
                proxies=proxies
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"API错误 (尝试 {attempt+1}/{max_retries}): {response.status_code}")
                print(f"响应: {response.text}")
                
        except Exception as e:
            print(f"请求失败 (尝试 {attempt+1}/{max_retries}): {e}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            
        if attempt < max_retries - 1:
            time.sleep(5)  # 等待5秒后重试
    
    return None


def test_gpqa_simple(num_questions: int = 2):
    """简单的GPQA测试"""
    print(f"=== 简单GPQA测试 ({num_questions}题) ===\n")
    
    # 加载数据集
    print("加载数据集...")
    dataset = load_dataset("Idavidrein/gpqa", "gpqa_main", split="train")
    print(f"成功加载 {len(dataset)} 道题目\n")
    
    results = []
    correct_count = 0
    
    for i in range(num_questions):
        print(f"\n{'='*60}")
        print(f"第 {i+1} 题")
        print(f"{'='*60}")
        
        item = dataset[i]
        
        # 获取问题和答案
        question = item["Question"]
        correct_answer = item["Correct Answer"]
        incorrect_answers = [
            item["Incorrect Answer 1"],
            item["Incorrect Answer 2"],
            item["Incorrect Answer 3"]
        ]
        
        # 过滤空答案并随机排序
        all_answers = [(correct_answer, True)] + [(ans, False) for ans in incorrect_answers if ans]
        random.seed(i)  # 固定随机种子
        random.shuffle(all_answers)
        
        # 找出正确答案的位置
        correct_letter = None
        options = []
        for j, (answer, is_correct) in enumerate(all_answers):
            letter = chr(65 + j)
            options.append(f"{letter}. {answer}")
            if is_correct:
                correct_letter = letter
        
        # 构建提示
        prompt = f"{question}\n\n"
        prompt += "\n".join(options)
        prompt += "\n\n请只回答字母 (A, B, C 或 D)。"
        
        # 显示问题预览
        print("\n问题预览（前300字符）:")
        print(prompt[:300] + "...\n")
        print(f"正确答案: {correct_letter}")
        
        # 调用API
        print("调用Grok-4...")
        response = call_grok_api(prompt)
        
        if response:
            print(f"模型原始回答: '{response}'")
            
            # 提取答案字母
            answer_letter = ""
            for char in response.strip().upper():
                if char in "ABCD":
                    answer_letter = char
                    break
            
            print(f"提取的答案: {answer_letter}")
            
            is_correct = answer_letter == correct_letter
            print(f"结果: {'✓ 正确' if is_correct else '✗ 错误'}")
            
            if is_correct:
                correct_count += 1
            
            results.append({
                "question_id": i,
                "expected": correct_letter,
                "actual": answer_letter,
                "raw_response": response,
                "correct": is_correct
            })
        else:
            print("API调用失败")
            results.append({
                "question_id": i,
                "expected": correct_letter,
                "error": "API call failed"
            })
    
    # 总结
    accuracy = correct_count / num_questions if num_questions > 0 else 0
    print(f"\n{'='*60}")
    print(f"测试完成: {correct_count}/{num_questions} 正确")
    print(f"准确率: {accuracy:.2%}")
    
    # 保存结果
    output = {
        "accuracy": accuracy,
        "correct": correct_count,
        "total": num_questions,
        "results": results
    }
    
    with open("simple_gpqa_results.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n结果已保存到 simple_gpqa_results.json")


if __name__ == "__main__":
    test_gpqa_simple(2)