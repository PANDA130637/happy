"""数据模型：候选人、分维度评分、评估结果。"""
from __future__ import annotations


class Candidate:
    """一份解析后的简历。"""

    def __init__(self, name: str, source: str, text: str, chunks: list | None = None):
        self.name = name
        self.source = source
        self.text = text
        self.chunks = chunks or []
        self.sections = {}  # section_key -> text

    def to_dict(self):
        return {
            "name": self.name,
            "source": self.source,
            "chars": len(self.text),
            "chunks": len(self.chunks),
            "sections": {k: len(v) for k, v in self.sections.items()},
        }


class CriterionScore:
    """JD 中某一条要求的评分与证据。"""

    def __init__(self, name: str, score: int = 0, evidence: list | None = None):
        self.name = name
        self.score = score          # 0-10
        self.evidence = evidence or []

    def to_dict(self):
        return {"name": self.name, "score": self.score, "evidence": self.evidence}


class Evaluation:
    """单个候选人的完整评估结果。"""

    RECO_LABELS = {"strong_interview", "interview", "maybe", "reject"}

    def __init__(self, candidate: str = "", jd_title: str = ""):
        self.candidate = candidate
        self.jd_title = jd_title
        self.overall_score = 0      # 0-100
        self.recommendation = ""    # strong_interview / interview / maybe / reject
        self.summary = ""
        self.criteria = []          # list[CriterionScore]
        self.strengths = []
        self.risks = []
        self.interview_questions = []
        self.raw = {}
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}

    def normalize_recommendation(self):
        if self.recommendation not in self.RECO_LABELS:
            self.recommendation = "maybe"

    def to_dict(self):
        return {
            "candidate": self.candidate,
            "jd_title": self.jd_title,
            "overall_score": self.overall_score,
            "recommendation": self.recommendation,
            "summary": self.summary,
            "criteria": [c.to_dict() for c in self.criteria],
            "strengths": self.strengths,
            "risks": self.risks,
            "interview_questions": self.interview_questions,
            "usage": self.usage,
        }