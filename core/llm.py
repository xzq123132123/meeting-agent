# -*- coding: utf-8 -*-
"""LLM 调用模块：OpenAI 兼容接口（豆包方舟 / OpenAI / DeepSeek / 智谱等通用）"""
import json
import re
import requests
import time

DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"


class LLMError(Exception):
    pass


def _extract_json(text: str):
    """从 LLM 输出中稳健提取 JSON。"""
    if not text:
        raise LLMError("模型返回为空")
    text = text.strip()

    # 1) 直接解析
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) 剥离 ```json ... ``` 代码块
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except Exception:
            pass

    # 3) 找第一个 { 到最后一个 }（平衡括号）
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 4) 平衡括号精确扫描
    for i, ch in enumerate(text):
        if ch == "{":
            depth = 0
            for j in range(i, len(text)):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[i:j + 1])
                        except Exception:
                            break
    raise LLMError("无法从模型输出中解析出 JSON")


def _check_ascii(name: str, value: str):
    """校验配置只含 ASCII 字符且无换行，防止误粘贴导致编码/请求头错误。"""
    if "\n" in value or "\r" in value:
        raise LLMError(
            f"「{name}」包含换行符，疑似多行粘贴。请重新复制，确保只保留单行内容。"
        )
    try:
        value.encode("ascii")
    except UnicodeEncodeError as e:
        start = max(0, e.start - 8)
        end = min(len(value), e.end + 8)
        bad = value[start:end]
        raise LLMError(
            f"「{name}」包含非英文字符（位置 {e.start}-{e.end}），疑似误粘贴了其他内容。"
            f"请只保留英文、数字与常见符号。附近内容：…{bad}…"
        )


def _post_chat(messages, base_url, api_key, model, temperature=0.3, timeout=120,
               max_retries=2, retry_delay=3):
    """调用 OpenAI 兼容 Chat Completions 接口，返回模型原始文本内容。"""
    _check_ascii("API Base URL", base_url)
    _check_ascii("API Key", api_key)
    _check_ascii("模型名称 / Endpoint ID", model)

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.exceptions.Timeout:
            last_err = LLMError(f"请求超时（>{timeout}s），请检查网络或模型负载")
        except requests.exceptions.ConnectionError as e:
            last_err = LLMError(f"网络连接失败：{e}")
        except Exception as e:
            last_err = LLMError(f"请求异常：{e}")
        else:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as e:
                    raise LLMError(f"响应缺少内容字段：{str(data)[:300]}")
                except Exception as e:
                    raise LLMError(f"响应解析失败：{e}")
            elif resp.status_code == 401:
                raise LLMError("API Key 无效或没有权限（401），请检查配置")
            elif resp.status_code == 404:
                # 模型名/接入点不存在：给出针对性排查
                body = resp.text[:500]
                if "InvalidEndpointOrModel" in body or "ModelNotFound" in body:
                    raise LLMError(
                        "模型名/接入点不存在或未开通（404）。请检查："
                        "① 「模型名称」框是否误填成了 API Key（Key 以 apikey- 开头，应填在「API Key」框）；"
                        "② 该模型是否已在火山方舟控制台「开通管理」中开通；"
                        "③ 填的是 Model ID（如 doubao-seed-1-6-251015）还是接入点 ID（ep- 开头）"
                    )
                raise LLMError(f"接口返回 404：{body}")
            elif resp.status_code == 429:
                last_err = LLMError("请求过于频繁（429），已触发限流")
            else:
                last_err = LLMError(
                    f"接口返回 {resp.status_code}：{resp.text[:300]}"
                )

        if attempt < max_retries:
            time.sleep(retry_delay)

    raise last_err or LLMError("未知错误")


def chat_json(messages, base_url, api_key, model, temperature=0.3, timeout=120,
              max_retries=2, retry_delay=3):
    """调用接口并返回解析后的 JSON（自动容错提取）。"""
    content = _post_chat(messages, base_url, api_key, model,
                         temperature=temperature, timeout=timeout,
                         max_retries=max_retries, retry_delay=retry_delay)
    return _extract_json(content)


def chat_text(messages, base_url, api_key, model, temperature=0.5, timeout=120,
              max_retries=2, retry_delay=3):
    """调用接口并返回原始文本（用于多轮对话、翻译、大纲等非 JSON 场景）。"""
    return _post_chat(messages, base_url, api_key, model,
                      temperature=temperature, timeout=timeout,
                      max_retries=max_retries, retry_delay=retry_delay).strip()


def is_configured(base_url, api_key, model):
    return bool(base_url and api_key and model)
