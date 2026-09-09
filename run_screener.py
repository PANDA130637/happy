"""命令行入口：对一批简历执行 Agent 初筛并生成报告。

用法：
    python run_screener.py --jd data/jd.txt --resumes data/resumes --out output
"""
from __future__ import annotations

import argparse
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

from screener import agent, jd_parser, llm, loader, ranker  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="简历筛选 Agent")
    ap.add_argument("--jd", default="data/jd.txt", help="岗位 JD 文件")
    ap.add_argument("--resumes", default="data/resumes", help="简历文件夹")
    ap.add_argument("--out", default="output", help="输出目录")
    ap.add_argument("--limit", type=int, default=0, help="最多处理前 N 份简历（0=全部）")
    args = ap.parse_args()

    print("== 1/3 解析 JD ==")
    jd_text = loader.load_jd(args.jd)
    jd_info = jd_parser.parse_jd(jd_text)
    print("岗位：", jd_info["title"])
    must = [r["name"] for r in jd_info["requirements"] if r["weight"] == "must"]
    plus = [r["name"] for r in jd_info["requirements"] if r["weight"] == "plus"]
    print("必须要求 %d 条：" % len(must))
    for m in must:
        print("  [必须]", m)
    print("加分要求 %d 条：" % len(plus))
    for p in plus:
        print("  [加分]", p)

    print("\n== 2/3 解析简历 ==")
    paths = loader.discover_resumes(args.resumes)
    if args.limit > 0:
        paths = paths[:args.limit]
    if not paths:
        print("未在 %s 找到简历文件" % args.resumes)
        sys.exit(1)
    candidates = [loader.load_candidate(p) for p in paths]
    for c in candidates:
        print("  - %s（%s，%d 字，%d 个证据句）" % (c.name, c.source, len(c.text), len(c.chunks)))

    print("\n== 3/3 Agent 逐份筛选 ==")
    evaluations = []
    for c in candidates:
        t0 = time.time()
        print("\n>> 正在筛选：%s ..." % c.name)
        ev = agent.screen(jd_info, c)
        used = ev.usage
        print("   总分 %d | 推荐 %s | 用时 %.1fs | tokens: %d in / %d out / %d 次调用" % (
            ev.overall_score, ev.recommendation, time.time() - t0,
            used.get("prompt_tokens", 0), used.get("completion_tokens", 0), used.get("calls", 0)))
        print("   结论：", (ev.summary or "")[:100])
        evaluations.append(ev)
        ranker.save_evaluation(args.out, ev)

    usage = llm.snapshot()
    ranker.save_summary(args.out, jd_info, evaluations, usage)
    report = ranker.build_report(jd_info, evaluations)
    report_path = args.out.rstrip("/\\") + "/report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print("\n==== 全部完成 ====")
    print("总 token：%d in / %d out / %d 次 API 调用" % (
        usage["prompt_tokens"], usage["completion_tokens"], usage["calls"]))
    print("报告已生成：%s" % report_path)
    print("逐份 JSON：%s/" % args.out)


if __name__ == "__main__":
    main()