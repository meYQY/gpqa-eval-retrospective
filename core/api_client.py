#!/usr/bin/env python3
"""
Grok API客户端
统一的API调用接口
"""

import time
import requests
import logging
from typing import Dict, Any, Optional
from ..configs.config import API_CONFIG, MODEL_CONFIG, get_api_key, get_proxy_config

logger = logging.getLogger(__name__)


class GrokAPIClient:
    """Grok API客户端"""
    
    def __init__(self):
        self.api_key = get_api_key()
        self.base_url = API_CONFIG["base_url"]
        self.timeout = API_CONFIG["timeout"]
        self.max_retries = API_CONFIG["max_retries"]
        self.retry_delay = API_CONFIG["retry_delay"]
        self.proxies = get_proxy_config()
        
    def call_api(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        调用Grok API
        
        Args:
            prompt: 提示文本
            **kwargs: 额外的模型参数
            
        Returns:
            API响应结果
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 合并默认参数和自定义参数
        model_params = MODEL_CONFIG.copy()
        model_params.update(kwargs)
        
        data = {
            "model": model_params.pop("default_model", "grok-4"),
            "messages": [{"role": "user", "content": prompt}],
            **model_params
        }
        
        # 重试逻辑
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=data,
                    timeout=self.timeout,
                    proxies=self.proxies
                )
                
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "content": result['choices'][0]['message']['content'],
                        "usage": result.get('usage', {}),
                        "model": result.get('model', 'unknown'),
                        "elapsed_time": elapsed_time
                    }
                else:
                    logger.error(f"API错误 - 状态码: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.error(f"请求超时 (尝试 {attempt+1}/{self.max_retries})")
                
            except Exception as e:
                logger.error(f"请求失败 (尝试 {attempt+1}/{self.max_retries}): {str(e)}")
            
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (attempt + 1)
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        return {
            "success": False,
            "error": "所有重试都失败",
            "elapsed_time": time.time() - start_time
        }
    
    def extract_answer(self, response: str) -> str:
        """
        从响应中提取答案字母
        
        Args:
            response: API响应文本
            
        Returns:
            答案字母（A/B/C/D）或空字符串
        """
        if not response:
            return ""
        
        response = response.strip().upper()
        
        # 直接匹配单个字母
        if len(response) == 1 and response in "ABCD":
            return response
        
        # 查找第一个出现的答案字母
        for char in response:
            if char in "ABCD":
                return char
        
        return ""