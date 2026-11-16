"""Input guardrails: run before any agent sees the question."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.config import MAX_QUERY_CHARS
from src.guardrails.policies import (GREETING, HYDERABAD_TERMS, INJECTION_PATTERNS, LEGAL_PATTERNS, MEDICAL_EMERGENCY,
                                     MEDICAL_PATTERNS, OFF_TOPIC_PATTERNS, OTHER_CITIES, PII_PATTERNS, REFUSALS,
                                     SAFETY_SENSITIVE, TOURISM_TERMS, UNSAFE_PATTERNS, find_terms, matches_any)


@dataclass
class GuardResult:
    allowed: bool
    category: str = "ok"
    message: str = ""
    clean_query: str = ""
    warnings: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def redact_pii(text: str) -> tuple[str, list[str]]:
    found: list[str] = []
    for label, pattern in PII_PATTERNS:
        if pattern.search(text):
            found.append(label)
            text = pattern.sub(f"[{label} removed]", text)
    return text, list(dict.fromkeys(found))


def check_input(query: str | None) -> GuardResult:
    q = (query or "").strip()
    if not q:
        return GuardResult(False, "empty", REFUSALS["empty"])
    if len(q) > MAX_QUERY_CHARS:
        return GuardResult(False, "too_long", REFUSALS["too_long"])
    q = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", q)  # zero-width / bidi tricks

    clean, pii = redact_pii(q)
    warnings = []
    if pii:
        warnings.append(f"For your privacy I removed personal details ({', '.join(pii)}) from your question. "
                        "There is no need to share them.")

    if MEDICAL_EMERGENCY.search(clean):
        return GuardResult(False, "medical_emergency", REFUSALS["medical_emergency"], clean, warnings)
    if matches_any(clean, INJECTION_PATTERNS):
        return GuardResult(False, "injection", REFUSALS["injection"], clean, warnings)
    if matches_any(clean, UNSAFE_PATTERNS):
        return GuardResult(False, "unsafe_illegal", REFUSALS["unsafe_illegal"], clean, warnings)
    if matches_any(clean, MEDICAL_PATTERNS):
        return GuardResult(False, "medical", REFUSALS["medical"], clean, warnings)
    if matches_any(clean, LEGAL_PATTERNS):
        return GuardResult(False, "legal", REFUSALS["legal"], clean, warnings)
    if GREETING.match(clean):
        return GuardResult(False, "greeting", REFUSALS["greeting"], clean, warnings)

    hyd = find_terms(clean, HYDERABAD_TERMS)
    others = find_terms(clean, OTHER_CITIES)
    if others and not hyd:
        return GuardResult(False, "other_city", REFUSALS["other_city"].format(city=others[0].title()), clean, warnings)
    if matches_any(clean, OFF_TOPIC_PATTERNS):
        return GuardResult(False, "off_topic", REFUSALS["off_topic"], clean, warnings)
    if not hyd and not find_terms(clean, TOURISM_TERMS):
        return GuardResult(False, "off_topic", REFUSALS["off_topic"], clean, warnings)

    flags = []
    if matches_any(clean, SAFETY_SENSITIVE):
        flags.append("safety_sensitive")
    if others:
        flags.append("mentions_other_city")
        warnings.append(f"VisitIQ only has information about Hyderabad, not {others[0].title()}.")
    return GuardResult(True, "ok", "", clean, warnings, flags)
