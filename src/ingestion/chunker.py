"""Chunking and prompt-injection sanitising of document text."""
from __future__ import annotations

import re

from src.config import CHUNK_OVERLAP, CHUNK_SIZE
from src.guardrails.policies import INJECTION_PATTERNS
from src.ingestion.loaders import Document


def sanitize_text(text: str) -> tuple[str, list[str]]:
    """Remove lines that look like prompt-injection attempts. Returns (clean_text, removed_lines)."""
    kept, removed = [], []
    for line in text.splitlines():
        if any(p.search(line) for p in INJECTION_PATTERNS):
            removed.append(line.strip())
        else:
            kept.append(line)
    return "\n".join(kept), removed


def _split_long(paragraph: str, size: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    pieces, buf = [], ""
    for s in sentences:
        while len(s) > size:
            pieces.append(s[:size])
            s = s[size:]
        if len(buf) + len(s) + 1 > size and buf:
            pieces.append(buf.strip())
            buf = ""
        buf += s + " "
    if buf.strip():
        pieces.append(buf.strip())
    return pieces


def _tail(text: str, overlap: int) -> str:
    if overlap <= 0 or len(text) <= overlap:
        return ""
    cut = text[-overlap:]
    space = cut.find(" ")
    return cut[space + 1:] if space != -1 else cut


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Paragraph-aware chunking with a word-aligned overlap between consecutive chunks."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n(?=[A-Z0-9][^\n]{0,60}\n)", text) if p.strip()]
    units: list[str] = []
    for p in paragraphs:
        units.extend(_split_long(p, size) if len(p) > size else [p])
    chunks, buf = [], ""
    for u in units:
        if buf and len(buf) + len(u) + 1 > size:
            chunks.append(buf.strip())
            buf = _tail(buf, overlap) + " "
        buf += u + "\n"
    if buf.strip():
        chunks.append(buf.strip())
    return chunks


def chunk_documents(docs: list[Document]) -> tuple[list[Document], list[str]]:
    """Split text documents into chunks; table rows stay one chunk each. Returns (chunks, removed_injection_lines)."""
    out: list[Document] = []
    removed_all: list[str] = []
    for doc in docs:
        clean, removed = sanitize_text(doc.text)
        removed_all.extend(removed)
        if doc.metadata.get("row") is not None:
            if clean.strip():
                out.append(Document(clean.strip(), {**doc.metadata, "chunk": 0}))
            continue
        for i, piece in enumerate(chunk_text(clean)):
            out.append(Document(piece, {**doc.metadata, "chunk": i}))
    return out, removed_all
