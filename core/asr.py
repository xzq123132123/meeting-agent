# -*- coding: utf-8 -*-
"""语音转写模块：OpenAI 兼容音频转写

支持两种调用方式，自动降级：
① POST {base_url}/audio/transcriptions（Whisper 风格 multipart 上传）
② POST {base_url}/chat/completions + input_audio（通义 qwen3-asr-flash 等）
"""
import base64
import time
import requests

from core.llm import LLMError, _check_ascii

AUDIO_MIME = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
}


def _safe_post(*args, **kwargs):
    """带重试的 POST：SSL/连接/超时等网络异常包装为 LLMError，瞬时错误重试 2 次。"""
    last_err = None
    for attempt in range(3):
        try:
            return requests.post(*args, **kwargs)
        except requests.exceptions.SSLError as e:
            last_err = LLMError(
                f"网络 SSL 连接异常（{e.__class__.__name__}），可能是网络/代理/防火墙拦截。"
                f"已自动重试第 {attempt + 1} 次"
            )
            time.sleep(1.5 * (attempt + 1))
        except requests.exceptions.ConnectionError as e:
            last_err = LLMError(f"网络连接失败：{e}")
            break
        except requests.exceptions.Timeout as e:
            last_err = LLMError(f"请求超时：{e}")
            break
    raise last_err or LLMError("网络请求失败")


def _try_multipart(base_url, api_key, model, file_bytes, filename, timeout=120):
    """方式 1：Whisper 风格 multipart 上传。"""
    url = base_url.rstrip("/") + "/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (filename, file_bytes, "application/octet-stream")}
    data = {"model": model, "response_format": "json"}
    resp = _safe_post(url, headers=headers, files=files, data=data, timeout=timeout)
    if resp.status_code == 200:
        j = resp.json()
        text = j.get("text", "")
        if text:
            return text
    raise LLMError(f"接口返回 {resp.status_code}：{resp.text[:300]}")


def _try_chat_audio(base_url, api_key, model, file_bytes, mime, timeout=120):
    """方式 2：chat/completions + input_audio（通义 qwen3-asr-flash 官方兼容方式）。"""
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    b64 = base64.b64encode(file_bytes).decode("ascii")
    data_uri = f"data:{mime};base64,{b64}"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": data_uri}}
                ],
            }
        ],
        "stream": False,
    }
    resp = _safe_post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code == 200:
        j = resp.json()
        try:
            return j["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise LLMError(f"响应缺少转写文本：{str(j)[:300]}")
    raise LLMError(f"接口返回 {resp.status_code}：{resp.text[:300]}")


def transcribe_audio(file_bytes, filename, base_url, api_key, model, timeout=180):
    """转写音频为文本。先试 multipart，失败后回退 chat+input_audio。"""
    _check_ascii("ASR Base URL", base_url)
    _check_ascii("API Key", api_key)
    _check_ascii("ASR 模型", model)

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "wav"
    mime = AUDIO_MIME.get(ext, "audio/wav")

    errs = []
    try:
        text = _try_multipart(base_url, api_key, model, file_bytes, filename, timeout)
        return text.strip()
    except LLMError as e:
        errs.append(f"① 文件上传方式：{e}")

    try:
        text = _try_chat_audio(base_url, api_key, model, file_bytes, mime, timeout)
        return text.strip()
    except LLMError as e:
        errs.append(f"② 音频输入方式：{e}")

    hint = ""
    if any("SSL" in s or "网络" in s for s in errs):
        hint = "\n\n如持续失败，请检查：① 网络代理/VPN 是否拦截了该域名；② 换一个网络环境（如手机热点）重试。"
    raise LLMError("两种转写方式均失败：\n" + "\n".join(errs) + hint)
