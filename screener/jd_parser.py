"""用 LLM 把岗位 JD 解析成结构化要求列表。"""
from __future__ import annotations

import json
import re

from . import llm, prompts


def _extract_json(text: str):
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M)
    try:
        return json.loads(text)
    except Exception:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


def parse_jd(jd_text: str) -> dict:
    messages = [
        {"role": "system", "content": prompts.JD_PARSE_SYSTEM},
        {"role": "user", "content": prompts.build_jd_parse_prompt(jd_text)},
    ]
    msg, _ = llm.chat(messages, json_mode=True)
    data = _extract_json(msg.content) or {}
    # 兜底默认值
    reqs = data.get("requirements") or []
    cleaned = []
    for r in reqs:
        if isinstance(r, dict) and r.get("name"):
            cleaned.append({
                "name": str(r.get("name", "")).strip(),
                "keywords": str(r.get("keywords", "")).strip(),
                "weight": "must" if r.get("weight") == "must" else "plus",
            })
    return {
        "title": str(data.get("title", "")).strip(),
        "summary": str(data.get("summary", "")).strip(),
        "requirements": cleaned,
    }