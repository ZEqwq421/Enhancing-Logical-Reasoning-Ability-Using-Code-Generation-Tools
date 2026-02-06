import os
import requests
from typing import Any
import time

BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

class DeepSeekAPIError(RuntimeError):
    pass

def call_llm(user_text: str, 
             system_text: str = "You are a helpful assistant.", 
             model: str = DEFAULT_MODEL, 
             max_tokens: int = 64, 
             stream: bool = False,
             )-> tuple[str, dict[str, Any]]:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key == None:
        raise DeepSeekAPIError("环境变量 DEEPSEEK_API_KEY 未设置。")

    url = f"{BASE_URL}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": max_tokens,
        "stream": stream,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        t0 = time.time()
        print("[DeepSeek] request start")
        resp = requests.post(url, headers=headers, json=payload, timeout=(10, 60))
        print(f"[DeepSeek] response {resp.status_code} in {time.time()-t0:.2f}s")
    except requests.RequestException as e:
        raise DeepSeekAPIError(f"网络请求失败：{e}") from e

    # 非 200 时，把服务端返回文本带出来，便于定位（401/402/429/5xx）
    if resp.status_code != 200:
        raise DeepSeekAPIError(f"HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    # 只取模型最终文本
    try:
        return data["choices"][0]["message"]["content"], data.get("usage", {})
    except (KeyError, IndexError, TypeError) as e:
        raise DeepSeekAPIError(f"响应结构异常：{data}") from e
"""
    200:成功(OK)
    401:没权限(Key错/没带)
    402:余额或计费问题
    429:请求太频繁
    500/503:服务器内部错误
"""