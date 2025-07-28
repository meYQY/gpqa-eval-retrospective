#!/usr/bin/env python3
"""
GPQA评测器配置文件
独立于DeepEval的配置管理
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# API配置
API_CONFIG = {
    "base_url": "https://api.x.ai/v1/chat/completions",
    "timeout": 900,  # 15分钟
    "max_retries": 3,
    "retry_delay": 5,  # 秒
}

# 模型配置
MODEL_CONFIG = {
    "default_model": "grok-4",
    "temperature": 0,
    "max_tokens": 100000,
}

# 数据集配置
DATASET_CONFIG = {
    "name": "Idavidrein/gpqa",
    "subset": "gpqa_main",
    "split": "train",
    "total_questions": 448,
}

# 文件路径配置
PATHS = {
    "checkpoint": PROJECT_ROOT / "results" / "gpqa_checkpoint.json",
    "logs_dir": PROJECT_ROOT / "logs",
    "results_dir": PROJECT_ROOT / "results",
}

# 监控配置
MONITOR_CONFIG = {
    "check_interval": 60,  # 秒
    "no_progress_threshold": 10,  # 无进展检查次数
    "auto_restart": True,
}

# 确保必要的目录存在
for path in PATHS.values():
    if path.suffix == "":  # 是目录
        path.mkdir(parents=True, exist_ok=True)

def get_api_key():
    """获取API密钥"""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 XAI_API_KEY")
    return api_key

def get_proxy_config():
    """获取代理配置"""
    proxy = os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY')
    if proxy:
        return {
            'http': os.environ.get('http_proxy', ''),
            'https': proxy
        }
    return {}