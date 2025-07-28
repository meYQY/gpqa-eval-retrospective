#!/usr/bin/env python3
"""
GPQA数据集加载器
处理数据集的加载和格式化
"""

import random
import logging
from typing import Dict, List, Tuple
from datasets import load_dataset
from ..configs.config import DATASET_CONFIG

logger = logging.getLogger(__name__)


class GPQADatasetLoader:
    """GPQA数据集加载器"""
    
    def __init__(self):
        self.dataset = None
        self.dataset_config = DATASET_CONFIG
        
    def load_dataset(self):
        """加载GPQA数据集"""
        logger.info(f"加载GPQA数据集: {self.dataset_config['subset']}")
        
        try:
            self.dataset = load_dataset(
                self.dataset_config['name'],
                self.dataset_config['subset'],
                split=self.dataset_config['split']
            )
            logger.info(f"成功加载 {len(self.dataset)} 道题目")
        except Exception as e:
            logger.error(f"从主数据源加载失败: {e}")
            logger.info("尝试备用数据源...")
            try:
                self.dataset = load_dataset(
                    "Wanfq/gpqa",
                    split=self.dataset_config['subset']
                )
                logger.info(f"成功从备用源加载 {len(self.dataset)} 道题目")
            except Exception as backup_error:
                logger.error(f"备用数据源也失败: {backup_error}")
                raise
        
        return self.dataset
    
    def format_question(self, item: Dict, question_id: int) -> Tuple[str, str]:
        """
        格式化题目为多选题格式
        
        Args:
            item: 原始题目数据
            question_id: 题目ID（用于随机种子）
            
        Returns:
            (格式化的题目, 正确答案字母)
        """
        question = item.get("Question", "")
        
        # 获取答案
        correct_answer = item.get("Correct Answer", "")
        incorrect_answers = [
            item.get("Incorrect Answer 1", ""),
            item.get("Incorrect Answer 2", ""),
            item.get("Incorrect Answer 3", "")
        ]
        
        # 创建答案列表
        all_answers = [(correct_answer, True)]
        all_answers.extend([(ans, False) for ans in incorrect_answers if ans])
        
        # 使用确定性随机打乱顺序
        random.seed(question_id)
        random.shuffle(all_answers)
        
        # 构建选项并记录正确答案
        options = []
        correct_letter = None
        
        for i, (answer, is_correct) in enumerate(all_answers):
            letter = chr(65 + i)  # A, B, C, D
            options.append(f"{letter}. {answer}")
            if is_correct:
                correct_letter = letter
        
        # 格式化题目
        formatted = f"{question}\n\n"
        formatted += "\n".join(options)
        formatted += "\n\n请只回答字母 (A, B, C 或 D)。"
        
        return formatted, correct_letter
    
    def get_question(self, question_id: int) -> Dict:
        """
        获取指定ID的题目
        
        Args:
            question_id: 题目ID
            
        Returns:
            题目数据
        """
        if not self.dataset:
            self.load_dataset()
        
        if question_id >= len(self.dataset):
            raise ValueError(f"题目ID {question_id} 超出范围（共{len(self.dataset)}题）")
        
        return self.dataset[question_id]
    
    def get_total_questions(self) -> int:
        """获取题目总数"""
        if not self.dataset:
            self.load_dataset()
        return len(self.dataset)