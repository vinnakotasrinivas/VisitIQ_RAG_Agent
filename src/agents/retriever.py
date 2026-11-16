"""Retriever agent: semantic search over the vector store, with light query expansion."""
from __future__ import annotations

import re

from src.agents.state import Constraints
from src.config import TOP_K
from src.vectordb.store import VectorStore


SPLIT = re.compile(r"\?|;|\band\b(?=\s+(?:how|what|where|when|which|who|is|are|can|do|does|should)\b)|\balso\b", re.I)


def sub_questions(query: str) -> list[str]:
    parts = [p.strip(" ,.") for p in SPLIT.split(query)]
    return [p for p in parts if len(p.split()) >= 3]


def retrieve(query: str, c: Constraints, intents: list[str], store: VectorStore, k: int = TOP_K) -> list[dict]:
    queries = [query]
    subs = sub_questions(query)
    if len(subs) > 1:
        queries.extend(subs)
    for name in c.attractions[:2]:
        queries.append(f"{name} opening hours tickets visitor tips")
    if "transport" in intents and (c.destination or c.attractions):
        queries.append(f"how to get to {c.destination or c.attractions[0]} by metro auto cab")
    if "itinerary" in intents and c.area:
        queries.append(f"things to see near {c.area} on {c.day or 'a weekday'}")
    if {"event"} & set(c.topics) or "itinerary" in intents:
        queries.append(f"evening events {c.area or ''} {c.day or ''}".strip())

    seen: dict[str, dict] = {}
    for i, q in enumerate(queries):
        for hit in store.search(q, k=k if i == 0 else 3):
            key = hit["text"][:120]
            if key not in seen or hit["similarity"] > seen[key]["similarity"]:
                seen[key] = hit
    hits = sorted(seen.values(), key=lambda h: h["similarity"], reverse=True)
    # prefer narrative sources (guides / FAQs) so explanations are grounded, keep the best table rows too
    narrative = [h for h in hits if h["metadata"].get("row") is None][:k]
    rows = [h for h in hits if h["metadata"].get("row") is not None][:3]
    return narrative + rows
