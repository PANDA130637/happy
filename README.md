# Resume Screener Agent（简历筛选 Agent）

一个基于 **DeepSeek Function Calling** 的真实 Agent 项目：输入一份岗位 JD + 一批简历（PDF/TXT/MD/DOCX），Agent 会**先调用工具在简历原文中检索证据，再逐条对照 JD 打分**，最终输出排名报告与每个候选人的评估 JSON。

> 设计动机：直接让大模型"凭印象"给简历打分会产生幻觉。本项目让模型像人一样先查证、再下结论——这是 Agent 开发中"工具调用 + 证据驱动"的标准范式。

## 核心亮点（写在简历上能讲清楚的点）

- **Function Calling / ReAct**：模型自主决定调用 `search_resume`（证据检索）与 `get_section`（查看完整板块）两个工具，多轮检索后才输出结论，而不是单次 Prompt 直接打分。
- **结构化输出**：每个候选人输出 `overall_score / recommendation / criteria(逐条要求评分+原文证据) / strengths / risks / interview_questions`，直接可入数据库或表格。
- **评测驱动迭代**：内置小型金标准评测集（`data/gold.json`），跑 `scripts/run_evals.py` 可量化推荐准确率，据此迭代 `screener/prompts.py`。
- **多格式简历解析**：PDF（pdfplumber/pypdf）、DOCX（纯标准库解析）、TXT/MD，中文简历自动分节（教育/实习/项目/技能）。

## 快速开始

```bash
# 1. 配置 DeepSeek key
cp .env.example .env      # 然后编辑 .env，填入 DEEPSEEK_API_KEY=sk-...

# 2. 安装依赖（建议 venv）
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 3. 跑通示例
python run_screener.py --jd data/jd.txt --resumes data/resumes --out output  # 默认 LangGraph 引擎
python run_screener.py --engine react --jd data/jd.txt --resumes data/resumes --out output  # 手写 ReAct 版

# 4. 跑评测（看推荐准确率）
python scripts/run_evals.py --jd data/jd.txt --gold data/gold.json --resumes data/resumes
```

把 `data/jd.txt` 换成真实 JD、把简历放进一个文件夹，即可对真实简历批量初筛。

## 项目结构

```
resume-screener-agent/
├── run_screener.py          # CLI：批量筛选 + 生成报告
├── screener/
│   ├── agent.py             # 手写 ReAct 版主循环（Function Calling + JSON 兜底）
│   ├── graph_agent.py       # LangGraph 状态图版（agent/tools 节点 + 条件路由）
│   ├── tools.py             # 工具定义与执行：search_resume / get_section
│   ├── loader.py            # 简历/JD 解析（PDF/DOCX/TXT/MD）+ 分节分句
│   ├── jd_parser.py         # 用 LLM 把 JD 解析成"必须/加分"要求清单
│   ├── prompts.py           # 提示词（集中管理，便于评测迭代）
│   ├── llm.py               # DeepSeek(OpenAI 兼容) 客户端 + token 统计
│   ├── ranker.py            # 排序 + Markdown/JSON 报告
│   └── models.py            # 数据模型
├── scripts/run_evals.py     # 金标准评测
├── data/                    # 示例 JD / 合成简历 / 金标准（仅用于演示）
└── output/                  # 生成的报告（gitignore）
```

## 工作流程

```
JD + 简历文件夹
   │
   ▼
[解析 JD] ──LLM──► 结构化要求清单（must/plus）
   │
   ▼
对每份简历：  Agent 循环
   ├─ 模型提出检索需求 → search_resume(证据) / get_section(板块)
   ├─ 多轮查证（最多 N 轮）
   └─ 输出最终 JSON（评分/推荐/证据/追问问题）
   │
   ▼
排序 → output/report.md + 逐份 JSON + summary.json
```

## 说明

- `data/` 下简历均为**合成的演示数据**，仅用于跑通流程与评测。
- 本项目用于招聘初筛的**辅助排序**，最终录用判断需人工复核。
- 成本提示：默认 `deepseek-chat`，每份简历通常消耗数千 token，量级约几分钱人民币，可在 `.env` 调整模型与 `MAX_TOKENS`。