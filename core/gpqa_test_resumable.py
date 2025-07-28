#!/usr/bin/env python3
"""
GPQA测试系统 - 支持断点续传版本
"""

import os
import json
import time
import datetime
from pathlib import Path
from dotenv import load_dotenv
from datasets import load_dataset
import requests
import random
import logging
from typing import Dict, List, Any, Set

# 加载环境变量
load_dotenv()

class ResumableGPQATestRunner:
    """支持断点续传的GPQA测试运行器"""
    
    def __init__(self, checkpoint_file: str = "gpqa_checkpoint.json", log_dir: str = "gpqa_logs"):
        """初始化测试运行器"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.checkpoint_file = checkpoint_file
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 设置日志
        self.setup_logging()
        
        # API配置
        self.api_key = os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("未设置 XAI_API_KEY")
        
        # 加载检查点
        self.checkpoint = self.load_checkpoint()
        
        # 统计信息
        self.stats = self.checkpoint.get("stats", {
            "total_time": 0,
            "api_calls": 0,
            "api_errors": 0,
            "timeouts": 0,
            "tokens_used": 0,
            "reasoning_tokens": 0
        })
        
        # 已完成的题目ID集合
        self.completed_questions = set(self.checkpoint.get("completed_questions", []))
        
        # 结果列表
        self.results = self.checkpoint.get("results", [])
        
        self.logger.info(f"已加载检查点，已完成 {len(self.completed_questions)} 题")
    
    def load_checkpoint(self) -> Dict:
        """加载检查点数据"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载检查点失败: {e}")
        return {}
    
    def save_checkpoint(self):
        """保存检查点数据"""
        checkpoint_data = {
            "timestamp": self.timestamp,
            "completed_questions": list(self.completed_questions),
            "results": self.results,
            "stats": self.stats,
            "last_saved": datetime.datetime.now().isoformat()
        }
        
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"检查点已保存，已完成 {len(self.completed_questions)} 题")
        except Exception as e:
            self.logger.error(f"保存检查点失败: {e}")
    
    def setup_logging(self):
        """设置日志系统"""
        log_file = self.log_dir / f"gpqa_test_{self.timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"GPQA测试系统启动 - 时间戳: {self.timestamp}")
    
    def call_grok_api(self, prompt: str, question_id: int) -> Dict[str, Any]:
        """调用Grok API并记录详细信息"""
        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "grok-4",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 100000
        }
        
        # 代理设置
        proxies = {}
        if os.environ.get('https_proxy'):
            proxies = {
                'http': os.environ.get('http_proxy', ''),
                'https': os.environ.get('https_proxy', '')
            }
        
        # 记录请求开始
        start_time = time.time()
        self.logger.info(f"[问题{question_id}] 开始API调用")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=data, 
                    timeout=900,  # 增加到15分钟，接近API服务端限制
                    proxies=proxies
                )
                
                elapsed_time = time.time() - start_time
                self.stats["api_calls"] += 1
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 记录token使用情况
                    usage = result.get('usage', {})
                    self.stats["tokens_used"] += usage.get('total_tokens', 0)
                    
                    # 记录推理token
                    completion_details = usage.get('completion_tokens_details', {})
                    self.stats["reasoning_tokens"] += completion_details.get('reasoning_tokens', 0)
                    
                    self.logger.info(
                        f"[问题{question_id}] API调用成功 - "
                        f"耗时: {elapsed_time:.2f}秒, "
                        f"总token: {usage.get('total_tokens', 0)}, "
                        f"推理token: {completion_details.get('reasoning_tokens', 0)}"
                    )
                    
                    return {
                        "success": True,
                        "content": result['choices'][0]['message']['content'],
                        "elapsed_time": elapsed_time,
                        "usage": usage,
                        "model": result.get('model', 'unknown')
                    }
                else:
                    self.stats["api_errors"] += 1
                    self.logger.error(
                        f"[问题{question_id}] API错误 - "
                        f"状态码: {response.status_code}, "
                        f"响应: {response.text[:200]}"
                    )
                    
            except requests.exceptions.Timeout:
                self.stats["timeouts"] += 1
                elapsed_time = time.time() - start_time
                self.logger.error(f"[问题{question_id}] 请求超时 (尝试 {attempt+1}/{max_retries}) - 耗时: {elapsed_time:.2f}秒")
                
            except Exception as e:
                self.stats["api_errors"] += 1
                elapsed_time = time.time() - start_time
                self.logger.error(f"[问题{question_id}] 请求失败 (尝试 {attempt+1}/{max_retries}) - 错误: {str(e)}")
            
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)  # 递增等待时间
                self.logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        # 所有重试都失败
        return {
            "success": False,
            "error": "所有重试都失败",
            "elapsed_time": time.time() - start_time
        }
    
    def run_test(self, start_idx: int = 0, num_questions: int = None):
        """运行GPQA测试，支持指定起始位置和数量"""
        overall_start = time.time()
        
        # 加载数据集
        self.logger.info("加载GPQA数据集...")
        dataset = load_dataset("Idavidrein/gpqa", "gpqa_main", split="train")
        total_dataset_size = len(dataset)
        self.logger.info(f"成功加载 {total_dataset_size} 道题目")
        
        # 确定要测试的题目范围
        if num_questions is None:
            num_questions = total_dataset_size - start_idx
        
        end_idx = min(start_idx + num_questions, total_dataset_size)
        actual_questions = end_idx - start_idx
        
        self.logger.info(f"=== 开始GPQA测试 (题目 {start_idx}-{end_idx-1}，共{actual_questions}题) ===")
        
        # 统计已完成的题目
        questions_to_test = []
        for i in range(start_idx, end_idx):
            if i not in self.completed_questions:
                questions_to_test.append(i)
        
        self.logger.info(f"需要测试 {len(questions_to_test)} 题（已完成 {actual_questions - len(questions_to_test)} 题）")
        
        # 处理每道题
        for idx, question_id in enumerate(questions_to_test):
            question_start = time.time()
            
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"处理第 {idx+1}/{len(questions_to_test)} 题 (题目ID: {question_id})")
            
            item = dataset[question_id]
            
            # 获取问题信息
            question = item["Question"]
            correct_answer = item["Correct Answer"]
            incorrect_answers = [
                item["Incorrect Answer 1"],
                item["Incorrect Answer 2"],
                item["Incorrect Answer 3"]
            ]
            
            # 记录问题信息
            question_log = {
                "question_id": question_id,
                "question_preview": question[:200] + "..." if len(question) > 200 else question,
                "question_length": len(question),
                "domain": item.get("High-level domain", "unknown"),
                "subdomain": item.get("Subdomain", "unknown")
            }
            
            # 随机排序答案
            all_answers = [(correct_answer, True)] + [(ans, False) for ans in incorrect_answers if ans]
            random.seed(question_id)
            random.shuffle(all_answers)
            
            # 找出正确答案位置
            correct_letter = None
            options = []
            for j, (answer, is_correct) in enumerate(all_answers):
                letter = chr(65 + j)
                options.append(f"{letter}. {answer}")
                if is_correct:
                    correct_letter = letter
            
            # 构建提示
            prompt = f"{question}\n\n" + "\n".join(options) + "\n\n请只回答字母 (A, B, C 或 D)。"
            
            # 调用API
            api_result = self.call_grok_api(prompt, question_id)
            
            if api_result["success"]:
                # 提取答案
                response = api_result["content"]
                answer_letter = ""
                for char in response.strip().upper():
                    if char in "ABCD":
                        answer_letter = char
                        break
                
                is_correct = answer_letter == correct_letter
                
                # 记录结果
                result = {
                    **question_log,
                    "expected": correct_letter,
                    "actual": answer_letter,
                    "raw_response": response,
                    "correct": is_correct,
                    "api_time": api_result["elapsed_time"],
                    "tokens_used": api_result.get("usage", {}).get("total_tokens", 0),
                    "reasoning_tokens": api_result.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens", 0),
                    "model": api_result.get("model", "unknown")
                }
                
                self.logger.info(
                    f"[问题{question_id}] 结果: {'✓ 正确' if is_correct else '✗ 错误'} "
                    f"(期望: {correct_letter}, 实际: {answer_letter})"
                )
            else:
                # API调用失败
                result = {
                    **question_log,
                    "expected": correct_letter,
                    "error": api_result["error"],
                    "api_time": api_result["elapsed_time"]
                }
            
            question_elapsed = time.time() - question_start
            result["total_time"] = question_elapsed
            
            # 添加到结果并标记为已完成
            self.results.append(result)
            self.completed_questions.add(question_id)
            
            self.logger.info(f"[问题{question_id}] 总耗时: {question_elapsed:.2f}秒")
            
            # 每10题保存一次检查点
            if (idx + 1) % 10 == 0:
                self.save_checkpoint()
                self.save_intermediate_report()
        
        # 最终保存
        self.save_checkpoint()
        
        # 生成最终报告
        self.generate_final_report()
    
    def save_intermediate_report(self):
        """保存中间结果报告"""
        # 计算当前统计
        correct_count = sum(1 for r in self.results if r.get("correct", False))
        total_count = len(self.results)
        accuracy = correct_count / total_count if total_count > 0 else 0
        
        intermediate_report = {
            "timestamp": self.timestamp,
            "total_completed": total_count,
            "correct": correct_count,
            "accuracy": accuracy,
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        # 保存简要报告
        with open(f"gpqa_intermediate_{self.timestamp}.json", 'w', encoding='utf-8') as f:
            json.dump(intermediate_report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"中间报告已保存 - 已完成: {total_count}, 准确率: {accuracy:.2%}")
    
    def generate_final_report(self):
        """生成最终报告"""
        # 计算统计数据
        correct_count = sum(1 for r in self.results if r.get("correct", False))
        total_count = len(self.results)
        accuracy = correct_count / total_count if total_count > 0 else 0
        
        # 生成完整报告
        report = {
            "test_info": {
                "timestamp": self.timestamp,
                "model": "grok-4",
                "dataset": "gpqa_main",
                "total_questions": total_count,
                "correct": correct_count,
                "accuracy": accuracy
            },
            "statistics": {
                **self.stats,
                "average_time_per_question": sum(r.get("total_time", 0) for r in self.results) / total_count if total_count > 0 else 0,
                "average_tokens_per_question": self.stats["tokens_used"] / total_count if total_count > 0 else 0
            },
            "detailed_results": self.results
        }
        
        # 保存详细报告
        report_file = self.log_dir / f"gpqa_report_{self.timestamp}.json"
        with open(report_file, "w", encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 打印总结
        self.logger.info("\n" + "="*60)
        self.logger.info("测试完成 - 总结报告")
        self.logger.info("="*60)
        self.logger.info(f"总题数: {total_count}")
        self.logger.info(f"正确数: {correct_count}")
        self.logger.info(f"准确率: {accuracy:.2%}")
        self.logger.info(f"API调用次数: {self.stats['api_calls']}")
        self.logger.info(f"API错误次数: {self.stats['api_errors']}")
        self.logger.info(f"超时次数: {self.stats['timeouts']}")
        self.logger.info(f"总Token使用: {self.stats['tokens_used']:,}")
        self.logger.info(f"推理Token: {self.stats['reasoning_tokens']:,}")
        self.logger.info(f"\n详细报告已保存到: {report_file}")


def main():
    """主函数"""
    import sys
    
    # 解析参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "resume":
            # 继续之前的测试
            runner = ResumableGPQATestRunner()
            # 继续测试剩余的题目
            runner.run_test(0, 448)  # 会自动跳过已完成的
        else:
            # 新的测试
            start_idx = 0
            num_questions = int(sys.argv[1])
            
            if len(sys.argv) > 2:
                start_idx = int(sys.argv[2])
            
            runner = ResumableGPQATestRunner()
            runner.run_test(start_idx, num_questions)
    else:
        print("用法:")
        print("  python gpqa_test_resumable.py <题目数量> [起始索引]")
        print("  python gpqa_test_resumable.py resume  # 继续之前的测试")


if __name__ == "__main__":
    main()