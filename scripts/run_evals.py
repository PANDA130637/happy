"""小型评测集：用标注好的金标准简历验证筛选 Agent 的推荐是否准确。

用法：
    python scripts/run_evals.py --jd data/jd.txt --gold data/gold.json --resumes data/resumes
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screener import agent, jd_parser, llm, loader  # noqa: E402

REC_LABEL_CN = {
    "strong_interview": "强烈推荐",
    "interview": "建议面试",
    "maybe": "备选",
    "reject": "不合适",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jd", default="data/jd.txt")
    ap.add_argument("--gold", default="data/gold.json")
    ap.add_argument("--resumes", default="data/resumes")
    args = ap.parse_args()

    with open(args.gold, encoding="utf-8") as f:
        gold = json.load(f)  # {filename: recommendation}

    jd_info = jd_parser.parse_jd(loader.load_jd(args.jd))
    print("评测 JD：", jd_info["title"], "\n")

    rows = []
    for filename, expect in gold.items():
        path = os.path.join(args.resumes, filename)
        if not os.path.exists(path):
            print("跳过（找不到文件）：", filename)
            continue
        cand = loader.load_candidate(path)
        ev = agent.screen(jd_info, cand)
        ok = ev.recommendation == expect
        rows.append((filename, expect, ev.recommendation, ev.overall_score, ok))
        print("%-28s gold=%-15s got=%-15s score=%3d  %s" % (
            filename, REC_LABEL_CN.get(expect, expect),
            REC_LABEL_CN.get(ev.recommendation, ev.recommendation),
            ev.overall_score, "OK" if ok else "MISMATCH"))

    if not rows:
        print("没有可评测的样本")
        return
    acc = sum(1 for r in rows if r[4]) / len(rows)
    usage = llm.snapshot()
    print("\n准确率（exact match）：%d/%d = %.0f%%" % (sum(1 for r in rows if r[4]), len(rows), acc * 100))
    print("总 token：%d in / %d out / %d 次调用" % (
        usage["prompt_tokens"], usage["completion_tokens"], usage["calls"]))
    print("说明：命中/未命中会显示为 OK / MISMATCH，可据此迭代 prompts.py 里的提示词。")


if __name__ == "__main__":
    main()