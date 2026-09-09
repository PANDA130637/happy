"""Agent 可调用的工具：在简历原文中检索证据（纯本地、无外部依赖）。

这是本项目 "Function Calling / 工具调用" 的体现：
模型不直接凭印象打分，而是先调用 search_resume / get_section
去简历原文里找证据，再基于证据给出结论，降低幻觉。
"""
from __future__ import annotations

import re

_STOPWORDS = {
    "的", "了", "和", "与", "及", "在", "是", "我", "有", "对", "为", "用",
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with",
    "使用", "负责", "参与", "进行", "完成", "相关", "以及", "等",
}

_TERM_RE = re.compile(r"[a-zA-Z0-9+#.\-]+|[\u4e00-\u9fff]")


def _terms(text: str) -> set:
    tokens = []
    for m in _TERM_RE.finditer(text.lower()):
        t = m.group(0)
        if t in _STOPWORDS or len(t) == 1:
            continue
        tokens.append(t)
    return set(tokens)


SECTION_LABEL_CN = {
    "summary": "个人简介",
    "education": "教育经历",
    "experience": "实习/工作经历",
    "projects": "项目经历",
    "skills": "技能",
    "other": "其他",
}


def search_resume(query: str, sentences: list, top_k: int = 5) -> str:
    """检索简历句子，返回与 query 最相关的前 top_k 条证据（含所属板块）。"""
    q_terms = _terms(query)
    if not q_terms:
        return "（无法从该查询提取关键词，请换一种说法）"
    scored = []
    for idx, item in enumerate(sentences):
        sent = item["text"]
        s_terms = _terms(sent)
        hit = len(q_terms & s_terms)
        if hit > 0:
            scored.append((hit, idx, item["section"], sent))
    scored.sort(key=lambda x: (-x[0], x[1]))
    top = scored[:top_k]
    if not top:
        return "（未在简历中找到与「%s」直接相关的表述）" % query
    lines = []
    for rank, (hit, _, section, sent) in enumerate(top, 1):
        label = SECTION_LABEL_CN.get(section, section)
        lines.append("[%d] (%s, 命中%d个关键词) %s" % (rank, label, hit, sent))
    return "\n".join(lines)


def get_section(section: str, sections: dict) -> str:
    """返回简历某一板块的完整原文。"""
    label = SECTION_LABEL_CN.get(section, section)
    body = sections.get(section, "")
    if not body:
        return "（简历中没有「%s」板块）" % label
    return "【%s】\n%s" % (label, body)


def build_tools_schema() -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": "search_resume",
                "description": (
                    "在候选人简历原文中检索与某条 JD 要求相关的证据片段。"
                    "打分前必须针对每条 JD 要求调用本工具找证据，不要凭印象判断。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "检索内容，例如：RAG 向量检索 项目、Python 技能、Function Calling",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回证据条数，默认 5",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_section",
                "description": "获取候选人简历某个板块的完整原文，用于深度核对。板块名：summary/education/experience/projects/skills/other。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "section": {
                            "type": "string",
                            "enum": ["summary", "education", "experience", "projects", "skills", "other"],
                        }
                    },
                    "required": ["section"],
                },
            },
        },
    ]


def run_tool(name: str, args: dict, candidate) -> str:
    """工具分发：把模型要调用的工具映射到真实函数。"""
    if name == "search_resume":
        return search_resume(args.get("query", ""), candidate.chunks, int(args.get("top_k", 5)))
    if name == "get_section":
        return get_section(args.get("section", ""), candidate.sections)
    return "（未知工具: %s）" % name