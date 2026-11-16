"""Output guardrails: applied to every answer before it is shown."""
from __future__ import annotations

import re

from src.guardrails.input_guard import redact_pii
from src.guardrails.policies import CHECK_BEFORE_YOU_GO, MEDICAL_PATTERNS, SAFETY_NOTE

LEAK_MARKERS = re.compile(r"(you are the (responder|planner)|system prompt:|RESPONDER_SYSTEM|### system)", re.I)
PRICE_OR_TIME = re.compile(r"(₹|\brs\.?\s?\d|\binr\b|\b\d{1,2}:\d{2}\b|\bticket|\bfare)", re.I)
ADVICE = re.compile(r"\b(you should take|take \d+ ?mg|recommended dose|consult (no|none))\b", re.I)


def finalise(answer: str, flags: list[str] | None = None) -> str:
    flags = flags or []
    text = (answer or "").strip()
    if LEAK_MARKERS.search(text):
        return "I can't share internal configuration. Please ask me about visiting Hyderabad."
    text, _ = redact_pii(text)
    if ADVICE.search(text) or (re.search(r"\bmg\b", text) and any(p.search(text) for p in MEDICAL_PATTERNS)):
        text = re.sub(ADVICE, "[medical advice removed]", text)
        text += "\n\nI can't give medical advice; please consult a doctor or call 108."
    extras = []
    if "safety_sensitive" in flags and "Safety note" not in text:
        extras.append(SAFETY_NOTE)
    if PRICE_OR_TIME.search(text) and "Check before you go" not in text:
        extras.append(CHECK_BEFORE_YOU_GO)
    if extras:
        text += "\n\n---\n" + "\n\n".join(extras)
    return text
