"""简历/JD 解析：支持 .txt/.md/.pdf/.docx，并做分节与分句预处理。"""
from __future__ import annotations

import os
import re
import zipfile
import xml.etree.ElementTree as ET

try:
    import pdfplumber
except Exception:  # pragma: no cover
    pdfplumber = None

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

from .models import Candidate

SECTION_ORDER = ["summary", "education", "experience", "projects", "skills", "other"]

HEADER_RULES = [
    ("summary", re.compile(r"(个人优势|个人简介|自我评价|关于我|自我介绍|综合素养)")),
    ("education", re.compile(r"(教育经历|教育背景|学习经历|在校经历|学历)")),
    ("experience", re.compile(r"(实习经历|工作经历|工作经验|实践经历|任职经历)")),
    ("projects", re.compile(r"(项目经历|项目经验|项目实践)")),
    ("skills", re.compile(r"(专业技能|技能工具|技能清单|技术栈|职业技能|技能)")),
    ("other", re.compile(r"(荣誉|获奖|证书|竞赛|校园|志愿|语言能力|外语)")),
]

_SENT_SPLIT = re.compile(r"[。！？!?；;\n]+")


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_plain(path: str) -> str:
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def extract_pdf(path: str) -> str:
    if pdfplumber is not None:
        try:
            parts = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    parts.append(page.extract_text() or "")
            return "\n".join(parts)
        except Exception:
            pass
    if PdfReader is not None:
        try:
            reader = PdfReader(path)
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            pass
    raise RuntimeError("无法解析 PDF，请安装 pdfplumber 或 pypdf")


def extract_docx(path: str) -> str:
    with zipfile.ZipFile(path) as z:
        xml_bytes = z.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paras = []
    for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        texts = [t.text or "" for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")]
        paras.append("".join(texts))
    return "\n".join(paras)


def extract_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md", ".markdown"):
        return read_plain(path)
    if ext == ".pdf":
        return extract_pdf(path)
    if ext == ".docx":
        return extract_docx(path)
    raise RuntimeError("不支持的简历格式: %s（支持 txt/md/pdf/docx）" % ext)


def split_sections(text: str) -> dict:
    """按常见简历标题把文本切分为 section -> text。"""
    sections = {k: [] for k in SECTION_ORDER}
    current = None
    for line in text.split("\n"):
        stripped = line.strip()
        matched = None
        for key, pattern in HEADER_RULES:
            if pattern.search(stripped) and len(stripped) <= 30:
                matched = key
                break
        if matched is not None:
            current = matched
            continue
        if current is None:
            sections["summary"].append(line)
        else:
            sections[current].append(line)
    return {k: clean_text("\n".join(v)) for k, v in sections.items() if clean_text("\n".join(v))}


def split_sentences(text: str, max_len: int = 200) -> list:
    """粗粒度分句（中英文），超长句再硬切。"""
    sentences = []
    for raw in _SENT_SPLIT.split(text):
        seg = raw.strip(" -–—|·\t")
        if not seg:
            continue
        if len(seg) <= max_len:
            sentences.append(seg)
            continue
        for i in range(0, len(seg), max_len):
            piece = seg[i:i + max_len].strip()
            if piece:
                sentences.append(piece)
    return sentences


def load_candidate(path: str) -> Candidate:
    text = clean_text(extract_text(path))
    name = os.path.splitext(os.path.basename(path))[0]
    sections = split_sections(text)
    sentences = []
    for key in SECTION_ORDER:
        body = sections.get(key, "")
        if body:
            for s in split_sentences(body):
                sentences.append({"section": key, "text": s})
    cand = Candidate(name=name, source=os.path.basename(path), text=text)
    cand.sections = sections
    cand.chunks = sentences
    return cand


def load_jd(path: str) -> str:
    return clean_text(extract_text(path))


def discover_resumes(folder: str) -> list:
    out = []
    for f in sorted(os.listdir(folder)):
        if os.path.splitext(f)[1].lower() in (".txt", ".md", ".markdown", ".pdf", ".docx"):
            out.append(os.path.join(folder, f))
    return out