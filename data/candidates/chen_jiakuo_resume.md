陈家阔
手机：13383082009 | 邮箱：236353927@qq.com | GitHub: https://github.com/PANDA130637/happy

个人优势
人工智能专业（211/双一流）在读，熟悉机器学习、深度学习与数据结构算法基础；理解大模型应用范式（Function Calling、ReAct、RAG 链路、Prompt 工程与评测迭代）；会用 LangGraph 做 Agent 工作流编排；深度使用 Codex、Claude Code 等 AI 编程工具，具备"自然语言提需求→Agent 生成代码→人工审查联调"的高效开发工作流；数据处理扎实，能把模糊需求拆解为可执行任务并量化交付。

教育经历
上海大学（211/双一流） 人工智能 本科 2024.09-今
主修：机器学习、深度学习基础、计算机视觉、Python 程序设计、线性代数、概率论与数理统计、数据结构与算法

项目经历
简历筛选 Agent（个人项目，2026.09，独立开发）
- 技术栈：Python、DeepSeek API（Function Calling）、LangGraph、ReAct、pypdf、Git、Codex/Claude Code
- 针对"招聘 JD 与大量简历匹配效率低、大模型直接打分易幻觉"问题，开发会"先查证、再打分"的简历筛选 Agent：输入 JD 与一批简历（PDF/DOCX/TXT/MD），自动输出候选人排名报告与结构化评估。
- 用 DeepSeek Function Calling 实现 ReAct 循环：模型自主调用 search_resume（检索简历原文证据）与 get_section（查看完整板块），证据齐全后才打分，避免幻觉；实现工具结果回填、多轮上下文与 API 断线自动重试。
- 用 LangGraph 把流程重构为显式状态图：agent（LLM 决策）与 tools（工具执行）两个节点 + 条件路由，state 用 reducer 自动累积多轮消息，recursion_limit 约束循环深度；与手写 ReAct 版双版本可对比，理解自研 vs 框架编排的取舍。
- 用 pypdf 与标准库实现 PDF/DOCX/TXT/MD 简历解析，中文简历自动分节（教育/实习/项目/技能）并分句构建可检索证据库；用 LLM 把自由文本 JD 解析为"必须/加分"要求清单。
- 输出结构化 JSON 与 Markdown 排名报告：总分/推荐级别/逐条评分(附原文证据)/亮点/风险/建议面试追问。
- 自建 3 份金标准简历评测集，根据评测暴露的"强候选人被低估、阈值偏严"问题迭代提示词，推荐准确率从 67% 提升到 100%（3/3）。
- 代码开源：https://github.com/PANDA130637/happy （README 含架构与复现命令）

2025 全国大学生数学建模竞赛（2025.09，负责数据处理与建模实现）
- 使用 pandas 清洗整理行业公开数据 500+ 条，完成缺失值/异常值处理与字段标准化，构建可复现建模数据集。
- 完成模型选型、特征构造与多轮调参评估，沉淀"数据清洗→特征工程→建模→评估优化"标准化流程。
- 全程用 Codex、Claude Code 辅助数据处理、可视化与论文结构化，独立完成 8000+ 字建模论文与 12 张标准化图表。

校园实践
世界教育者大会 媒体宣传（2026.08）：负责大会影像素材产出与公众号推文配图交付，累计支撑 12 篇推文、总阅读量 2.3 万；会后完成全流程复盘并输出可复用的素材交付规范，具备需求对接、文档撰写与跨团队协作经验。

专业技能
- 编程：Python（pandas）、数据结构与算法、OOP 基础、Git、MySQL、Excel
- LLM/Agent：DeepSeek API、Function Calling、LangGraph、ReAct、RAG 基础、Prompt 工程与评测、pypdf
- AI 工具：Codex、Claude Code
- 语言：英语 CET-6（可阅读英文技术文档）