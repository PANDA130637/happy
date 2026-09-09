"""LangGraph 版筛选 Agent：把手写 ReAct 循环重构为显式状态图。

图结构：
    START -> agent --(有 tool_calls)--> tools -> agent
                  --(无 tool_calls，已输出最终 JSON)--> END

- agent 节点：LLM 决策，返回 assistant 消息（可能带 tool_calls）
- tools 节点：逐个执行工具，把 role=tool 的结果回填
- 条件路由 + recursion_limit：用图本身约束循环深度，防止死循环

对比手写 while 循环版（agent.py）：
- 节点/边/状态显式化，流程可观测、可扩展（如新增"复核节点"只需加节点和边）
- 状态用 reducer(operator.add) 自动累积消息
"""
from __future__ import annotations

import json
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from . import config as cfg
from . import llm, tools
from .agent import _extract_json, _to_evaluation  # 复用 JSON 解析与结果映射

_TOOL_SCHEMA = tools.build_tools_schema()


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]


def _to_message_dict(message) -> dict:
    """把 openai 返回的 message 对象序列化为对话字典。"""
    d = {"role": "assistant", "content": message.content or ""}
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
            }
            for tc in tool_calls
        ]
    return d


def _parse_args(raw: str) -> dict:
    try:
        args = json.loads(raw or "{}")
        return args if isinstance(args, dict) else {}
    except Exception:
        return {}


def build_graph(candidate):
    """为某个候选人构建并编译 LangGraph 状态图。"""

    def agent_node(state: AgentState):
        message, _ = llm.chat(state["messages"], tools=_TOOL_SCHEMA)
        return {"messages": [_to_message_dict(message)]}

    def tools_node(state: AgentState):
        last = state["messages"][-1]
        outputs = []
        for tc in last.get("tool_calls", []):
            args = _parse_args(tc.get("function", {}).get("arguments"))
            result = tools.run_tool(tc["function"]["name"], args, candidate)
            outputs.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
        return {"messages": outputs}

    def router(state: AgentState):
        last = state["messages"][-1]
        return "tools" if last.get("tool_calls") else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", router, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def screen_graph(jd_info: dict, candidate) -> object:
    """LangGraph 版入口，签名与 agent.screen 一致，可直接替换。"""
    from . import prompts

    before = llm.snapshot()
    init_messages = [
        {"role": "system", "content": prompts.SCREENER_SYSTEM},
        {"role": "user", "content": prompts.build_user_prompt(jd_info, candidate)},
    ]

    final_content = ""
    try:
        graph = build_graph(candidate)
        # 每个 agent/tools 来回算 2 步；recursion_limit 兜底防死循环
        result = graph.invoke({"messages": init_messages},
                              {"recursion_limit": cfg.MAX_TOOL_ROUNDS * 2 + 5})
        final_content = (result["messages"][-1].get("content") or "")
    except Exception:
        final_content = ""  # 超限/异常 → 走下方强制 JSON 兜底

    data = _extract_json(final_content)
    if data is None:
        fallback = list(init_messages)
        if final_content:
            fallback.append({"role": "assistant", "content": final_content})
        fallback.append({
            "role": "user",
            "content": "请停止调用工具，直接输出符合 JSON Schema 的最终评估 JSON，不要输出任何多余文字。",
        })
        msg, _ = llm.chat(fallback, json_mode=True)
        data = _extract_json(msg.content) or {}
    return _to_evaluation(candidate, jd_info, data, llm.delta(before))