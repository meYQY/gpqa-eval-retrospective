#!/usr/bin/env python3
"""
环境配置验证脚本
在运行评测前检查所有配置是否正确
"""

import os
import sys
import json
from pathlib import Path

# 添加父目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from configs.config import *
from core.api_client import call_grok_api

def verify_environment():
    """评测前验证环境配置"""
    
    print("=== GPQA Environment Verification ===\n")
    
    errors = []
    warnings = []
    
    # 1. 检查 API Key
    print("1. Checking API Key...")
    if not GROK_API_KEY:
        errors.append("❌ GROK_API_KEY not set! Please set it in environment variables.")
    else:
        print(f"✓ API key loaded (length: {len(GROK_API_KEY)})")
    
    # 2. 测试 API 连接
    print("\n2. Testing API connection...")
    if GROK_API_KEY:
        try:
            test_prompt = "Reply with just 'OK'"
            response = call_grok_api(test_prompt, max_tokens=10)
            if "OK" in response:
                print("✓ API connection successful")
            else:
                warnings.append(f"⚠️  Unexpected API response: {response[:50]}...")
        except Exception as e:
            errors.append(f"❌ API test failed: {str(e)}")
    
    # 3. 检查配置参数
    print("\n3. Checking configuration...")
    if TEMPERATURE != 0:
        warnings.append(f"⚠️  Temperature is {TEMPERATURE} (should be 0 for reproducibility)")
    else:
        print(f"✓ Temperature: {TEMPERATURE}")
    
    if MAX_TOKENS < 1000:
        warnings.append(f"⚠️  MAX_TOKENS is {MAX_TOKENS} (may be too low for complex questions)")
    else:
        print(f"✓ Max tokens: {MAX_TOKENS}")
    
    if TIMEOUT < 60:
        warnings.append(f"⚠️  Timeout is {TIMEOUT}s (may be too short for complex questions)")
    else:
        print(f"✓ Timeout: {TIMEOUT}s")
    
    print(f"✓ Max retries: {MAX_RETRIES}")
    print(f"✓ Model: {MODEL_NAME}")
    
    # 4. 检查数据文件
    print("\n4. Checking data files...")
    data_path = Path(PROCESSED_DATA)
    if not data_path.exists():
        errors.append(f"❌ Processed data not found: {PROCESSED_DATA}")
        print(f"   Run: python scripts/preprocess_gpqa.py")
    else:
        with open(data_path, 'r') as f:
            data = json.load(f)
        print(f"✓ Processed data found: {len(data)} questions")
    
    # 5. 检查目录权限
    print("\n5. Checking directory permissions...")
    dirs_to_check = [
        Path(RESULTS_DIR),
        Path(CHECKPOINT_FILE).parent,
        Path(LOG_FILE).parent if LOG_FILE else Path("logs")
    ]
    
    for dir_path in dirs_to_check:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            test_file = dir_path / "test.tmp"
            test_file.write_text("test")
            test_file.unlink()
            print(f"✓ Can write to: {dir_path}")
        except Exception as e:
            errors.append(f"❌ Cannot write to {dir_path}: {e}")
    
    # 6. 检查 checkpoint
    print("\n6. Checking checkpoint...")
    checkpoint_path = Path(CHECKPOINT_FILE)
    if checkpoint_path.exists():
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
        completed = checkpoint.get('current_index', 0)
        print(f"⚠️  Found existing checkpoint at question {completed}/448")
        print("   The evaluation will resume from this point.")
    else:
        print("✓ No checkpoint found, will start from beginning")
    
    # 总结
    print("\n" + "="*50)
    if errors:
        print("\n❌ Verification FAILED with errors:")
        for error in errors:
            print(f"   {error}")
        return False
    
    if warnings:
        print("\n⚠️  Warnings:")
        for warning in warnings:
            print(f"   {warning}")
    
    print("\n✅ All checks passed! Ready to run evaluation.")
    return True

if __name__ == "__main__":
    success = verify_environment()
    sys.exit(0 if success else 1)