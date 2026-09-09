# -*- coding: utf-8 -*-
"""ASR 语音转写模块测试（mock 网络，验证降级逻辑）"""
import io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest import mock
from core import asr
from core.llm import LLMError

WAV_BYTES = b"\x00\x01\x02" * 100


class FakeResp:
    def __init__(self, status, text):
        self.status_code = status
        self._text = text

    @property
    def text(self):
        return self._text

    def json(self):
        import json as _json
        return _json.loads(self._text)


# 1) multipart 成功（OpenAI whisper 风格）
with mock.patch("requests.post") as m:
    m.return_value = FakeResp(200, '{"text": "会议开始，讨论裂缝检测方案"}')
    text = asr.transcribe_audio(WAV_BYTES, "meeting.wav", "https://x.com/v1", "sk-1", "whisper-1")
    assert "裂缝检测" in text
    # 确认走的是 multipart 端点
    assert "/audio/transcriptions" in m.call_args.args[0]
    print("1. multipart 方式 OK ->", text[:20], "...")

# 2) multipart 404 → 回退 chat+input_audio 成功（通义 qwen3-asr-flash 风格）
with mock.patch("requests.post") as m:
    m.side_effect = [
        FakeResp(404, '{"error": "not found"}'),
        FakeResp(200, '{"choices": [{"message": {"content": "语音转写结果：数据增强对比实验"}}]}'),
    ]
    text = asr.transcribe_audio(WAV_BYTES, "meeting.mp3", "https://dashscope.aliyuncs.com/compatible-mode/v1", "sk-1", "qwen3-asr-flash")
    assert "数据增强" in text
    assert "/chat/completions" in m.call_args_list[1].args[0]
    print("2. 自动回退 chat 方式 OK ->", text[:20], "...")

# 3) 两种方式都失败 → 报错信息含两种原因
with mock.patch("requests.post") as m:
    m.side_effect = [
        FakeResp(404, '{"error": "a"}'),
        FakeResp(500, '{"error": "b"}'),
    ]
    try:
        asr.transcribe_audio(WAV_BYTES, "meeting.wav", "https://x.com/v1", "sk-1", "m")
        assert False, "应当抛错"
    except LLMError as e:
        assert "两种转写方式均失败" in str(e)
        assert "文件上传方式" in str(e) and "音频输入方式" in str(e)
        print("3. 双失败降级提示 OK")

# 4) 非 ASCII 配置拦截
try:
    asr.transcribe_audio(WAV_BYTES, "m.wav", "https://x.com/v1", "sk-中文", "m")
    assert False, "应当抛错"
except LLMError as e:
    assert "非英文字符" in str(e)
    print("4. 配置校验 OK")

# 5) SSL 异常：multipart 重试 3 次全失败 → 自动回退 chat 成功
from requests.exceptions import SSLError as ReqSSLError
class FakeChatResp:
    status_code = 200
    @property
    def text(self): return ""
    def json(self): return {"choices": [{"message": {"content": "SSL 回退后的转写结果"}}]}
with mock.patch("requests.post") as m:
    # 前 3 次（multipart 重试）SSL 失败，第 4 次（chat）成功
    m.side_effect = [ReqSSLError("EOF occurred in violation of protocol")] * 3 + [FakeChatResp()]
    text = asr.transcribe_audio(WAV_BYTES, "m.wav", "https://dashscope.aliyuncs.com/compatible-mode/v1", "sk-1", "qwen3-asr-flash")
    assert "SSL 回退" in text
    chat_call = [c for c in m.call_args_list if "/chat/completions" in c.args[0]]
    assert chat_call, "应回退到 chat 端点"
    print("5. SSL 异常自动回退 OK")

# 6) 全程 SSL 失败 → 报错含网络排查提示
with mock.patch("requests.post") as m:
    m.side_effect = ReqSSLError("EOF occurred in violation of protocol")
    try:
        asr.transcribe_audio(WAV_BYTES, "m.wav", "https://dashscope.aliyuncs.com/compatible-mode/v1", "sk-1", "qwen3-asr-flash")
        assert False, "应当抛错"
    except LLMError as e:
        assert "网络" in str(e) and "代理" in str(e), str(e)
        print("6. 全程 SSL 失败给出网络排查提示 OK")

print()
print("ASR TESTS PASSED")
