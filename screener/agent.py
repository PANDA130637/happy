"""筛选 Agent 主循环：ReAct 式 Function Calling。

流程（每个候选人）：
1. 系统提示 + 用户消息（JD + 简历预览）→ 模型决定调用哪些工具
2. 模型反复调用 search_resume / get_section 检索简历原文证据
3. 模型停止调用工具并输出最终 JSON（overall_score / recommendation / criteria / ...）
4. 若输出不是合法 JSON，追加一次强制 JSON 调用兜底
"""
from __future__ import annotations

import json
import re

from . import llm, tools
from . import config as cfg
from .models import Evaluation, CriterionScore

_TOOL_SCHEMA = tools.build_tools_schema()


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


def _pick(data: dict, *keys, default=None):
    for k in keys:
        if k in data and data[k] not in (None, ""):
            return data[k]
    return default


def _as_int(value, lo, hi, default):
    try:
        v = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def _to_evaluation(candidate, jd_info: dict, data: dict, usage: dict) -> Evaluation:
    ev = Evaluation(candidate=candidate.name, jd_title=jd_info.get("title", ""))
    ev.overall_score = _as_int(_pick(data, "overall_score", "总分"), 0, 100, 0)
    ev.recommendation = str(_pick(data, "recommendation", "推荐", default="maybe"))
    ev.summary = str(_pick(data, "summary", "结论", default=""))
    ev.raw = data

    criteria = _pick(data, "criteria", "scores", "维度评分", default=[]) or []
    for c in criteria:
        if isinstance(c, dict) and c.get("name"):
            ev.criteria.append(CriterionScore(
                name=str(c.get("name")),
                score=_as_int(c.get("score", 0), 0, 10, 0),
                evidence=[str(e) for e in (c.get("evidence") or []) if str(e).strip()],
            ))

    for key in ("strengths", "优势", "亮点"):
        val = _pick(data, key, default=[])
        if isinstance(val, list):
            ev.strengths = [str(x) for x in val if str(x).strip()]
            break
    for key in ("risks", "风险", "短板"):
        val = _pick(data, key, default=[])
        if isinstance(val, list):
            ev.risks = [str(x) for x in val if str(x).strip()]
            break
    for key in ("interview_questions", "面试问题", "questions"):
        val = _pick(data, key, default=[])
        if isinstance(val, list):
            ev.interview_questions = [str(x) for x in val if str(x).strip()]
            break

    ev.normalize_recommendation()
    ev.usage = usage
    return ev


def screen(jd_info: dict, candidate) -> Evaluation:
    from . import prompts
    messages = [
        {"role": "system", "content": prompts.SCREENER_SYSTEM},
        {"role": "user", "content": prompts.build_user_prompt(jd_info, candidate)},
    ]
    before = llm.snapshot()

    final_content = None
    for _round in range(cfg.MAX_TOOL_ROUNDS):
        msg, _ = llm.chat(messages, tools=_TOOL_SCHEMA)
        tool_calls = getattr(msg, "tool_calls", None) or []
        if tool_calls:
            assistant_msg = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                    }
                    for tc in tool_calls
                ],
            }
            messages.append(assistant_msg)
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    if not isinstance(args, dict):
                        args = {}
                except Exception:
                    args = {}
                result = tools.run_tool(tc.function.name, args, candidate)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            continue
        # 模型选择直接输出最终结果
        final_content = msg.content or ""
        data = _extract_json(final_content)
        if data is not None:
            return _to_evaluation(candidate, jd_info, data, llm.delta(before))
        break

    # 兜底：强制一次纯 JSON 输出
    messages.append({
        "role": "user",
        "content": "请停止调用工具，直接输出符合 JSON Schema 的最终评估 JSON，不要输出任何多余文字。",
    })
    msg, _ = llm.chat(messages, json_mode=True)
    final_content = msg.content or ""
    data = _extract_json(final_content) or {}
    return _to_evaluation(candidate, jd_info, data, llm.delta(before))