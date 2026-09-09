# -*- coding: utf-8 -*-
"""文本与文件解析：清洗、读取 txt/docx/md、长文本分块"""
import re
import os
import docx


def clean_text(text: str) -> str:
    """清洗原始文本：去首尾空白、压缩空行、规整标点空格。"""
    if not text:
        return ""
    # 统一换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 去掉每行首尾多余空白
    lines = [line.strip() for line in text.split("\n")]
    # 压缩连续空行
    cleaned = []
    blank = 0
    for line in lines:
        if not line:
            blank += 1
            if blank <= 1:
                cleaned.append("")
        else:
            blank = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def read_txt(path: str) -> str:
    for enc in ("utf-8", "gbk", "utf-8-sig"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def read_docx(path: str) -> str:
    doc = docx.Document(path)
    parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text.strip())
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            parts.append(" | ".join(cells))
    return "\n".join(parts)


def read_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".docx",):
        return read_docx(path)
    if ext in (".txt", ".md", ".csv", ".log"):
        return read_txt(path)
    raise ValueError(f"不支持的文件类型：{ext}（支持 txt / md / csv / log / docx）")


def split_chunks(text: str, max_chars: int = 9000) -> list:
    """长文本按段落切块，保证每块不超过 max_chars，优先在空行处切。"""
    if len(text) <= max_chars:
        return [text]
    paragraphs = re.split(r"\n\s*\n", text)
    chunks, cur = [], ""
    for p in paragraphs:
        if len(cur) + len(p) + 2 > max_chars and cur:
            chunks.append(cur)
            cur = p
        else:
            cur = cur + "\n\n" + p if cur else p
    if cur:
        chunks.append(cur)
    return chunks
