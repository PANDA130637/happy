"""结果落盘：单个候选人 JSON、汇总 JSON、人类可读的 Markdown 报告。"""
from __future__ import annotations

import json
import os

REC_LABEL_CN = {
    "strong_interview": "强烈推荐面试",
    "interview": "建议面试",
    "maybe": "备选/观望",
    "reject": "不合适",
}
REC_ORDER = {"strong_interview": 0, "interview": 1, "maybe": 2, "reject": 3}


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def save_evaluation(out_dir: str, ev) -> str:
    ensure_dir(out_dir)
    safe = "".join(ch for ch in ev.candidate if ch.isalnum() or ch in "-_") or "candidate"
    path = os.path.join(out_dir, safe + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ev.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def save_summary(out_dir: str, jd_info: dict, evaluations: list, usage: dict) -> str:
    ensure_dir(out_dir)
    path = os.path.join(out_dir, "summary.json")
    data = {
        "jd": jd_info,
        "ranked": [ev.to_dict() for ev in evaluations],
        "total_usage": usage,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _md_escape(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def build_report(jd_info: dict, evaluations: list) -> str:
    ranked = sorted(evaluations, key=lambda e: (-e.overall_score, REC_ORDER.get(e.recommendation, 9)))
    lines = []
    lines.append("# 简历筛选报告（Agent 自动初筛）\n")
    lines.append("## 岗位：" + (jd_info.get("title") or "（未命名）") + "\n")
    if jd_info.get("summary"):
        lines.append("> " + jd_info["summary"] + "\n")
    lines.append("## 排名总览\n")
    lines.append("| 排名 | 候选人 | 总分 | 推荐 | 一句话结论 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for i, ev in enumerate(ranked, 1):
        lines.append("| %d | %s | %d | %s | %s |" % (
            i, _md_escape(ev.candidate), ev.overall_score,
            REC_LABEL_CN.get(ev.recommendation, ev.recommendation),
            _md_escape(ev.summary[:80])))
    lines.append("")
    for i, ev in enumerate(ranked, 1):
        lines.append("---\n")
        lines.append("## %d. %s　（%d 分 / %s）\n" % (
            i, _md_escape(ev.candidate), ev.overall_score,
            REC_LABEL_CN.get(ev.recommendation, ev.recommendation)))
        lines.append(_md_escape(ev.summary) + "\n")
        lines.append("### 分维度评分")
        lines.append("| JD 要求 | 评分(0-10) | 命中的证据 |")
        lines.append("| --- | --- | --- |")
        for c in ev.criteria:
            evidence = "<br>".join(_md_escape(e) for e in c.evidence[:3]) or "-"
            lines.append("| %s | %d | %s |" % (_md_escape(c.name), c.score, evidence))
        lines.append("")
        lines.append("**亮点：**")
        for s in ev.strengths[:4]:
            lines.append("- " + _md_escape(s))
        lines.append("")
        lines.append("**风险/短板：**")
        for r in ev.risks[:3]:
            lines.append("- " + _md_escape(r))
        lines.append("")
        lines.append("**建议面试追问：**")
        for q in ev.interview_questions[:3]:
            lines.append("- " + _md_escape(q))
        lines.append("")
    lines.append("\n---\n*本报告由 resume-screener-agent 自动生成，仅用于初筛排序，最终判断请结合人工复核。*")
    return "\n".join(lines)