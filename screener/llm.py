"""DeepSeek(OpenAI 兼容) 客户端封装 + token 用量统计 + 网络重试。"""
from __future__ import annotations

import time

from openai import OpenAI
from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

from . import config

_client = None
_STATS = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
_MAX_RETRIES = 3
_RETRYABLE = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)


def get_client() -> OpenAI:
    global _client
    config.check_api_key()
    if _client is None:
        _client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            max_retries=2,
            timeout=120.0,
        )
    return _client


def snapshot() -> dict:
    return dict(_STATS)


def delta(before: dict) -> dict:
    return {k: _STATS[k] - before.get(k, 0) for k in _STATS}


def chat(messages: list, tools: list | None = None, json_mode: bool = False,
         temperature: float | None = None, max_tokens: int | None = None):
    client = get_client()
    kwargs = {
        "model": config.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": config.TEMPERATURE if temperature is None else temperature,
        "max_tokens": max_tokens or config.MAX_TOKENS,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(**kwargs)
            usage = resp.usage
            _STATS["prompt_tokens"] += usage.prompt_tokens or 0
            _STATS["completion_tokens"] += usage.completion_tokens or 0
            _STATS["calls"] += 1
            return resp.choices[0].message, resp
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(3 * attempt)
    raise last_exc