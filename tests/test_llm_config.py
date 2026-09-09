# -*- coding: utf-8 -*-
"""LLM 配置校验测试"""
import io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import llm

# 1) 正常 ASCII 配置不报错（只校验，不发起真实网络请求）
llm._check_ascii("API Key", "sk-test123")
llm._check_ascii("模型", "qwen-plus")
print("1. 纯 ASCII 配置通过 OK")

# 2) 含中文的配置应报 LLMError 且提示清晰
try:
    llm._check_ascii("API Key", "sk-123中文误粘贴")
    assert False, "应当抛错"
except llm.LLMError as e:
    assert "非英文字符" in str(e), str(e)
    print("2. 中文检测 OK ->", str(e)[:50], "...")

# 3) 全角符号检测
try:
    llm._check_ascii("模型名称", "qwen－plus")
    assert False, "应当抛错"
except llm.LLMError as e:
    print("3. 全角符号检测 OK")

# 4) 换行混入检测
try:
    llm._check_ascii("API Key", "sk-abc\nsk-def")
    assert False, "应当抛错"
except llm.LLMError as e:
    assert "换行符" in str(e), str(e)
    print("4. 换行混入检测 OK")

# 5) emoji / 特殊符号检测
try:
    llm._check_ascii("模型名称", "qwen-plus✨")
    assert False, "应当抛错"
except llm.LLMError as e:
    print("5. emoji 检测 OK")

print()
print("LLM CONFIG VALIDATION TESTS PASSED")
