"""Validator agent: deterministic checks that the draft is grounded and the itinerary is feasible."""
from __future__ import annotations

import re

from src.agents.data_analyst import DataAnalyst, to_min
from src.agents.responder import SourceBook

CITE = re.compile(r"\[S(\d+)\]")
MONEY = re.compile(r"(?:₹|\brs\.?\s?|\binr\s?)(\d[\d,]*)", re.I)
TIME = re.compile(r"\b(\d{1,2}):(\d{2})\b")
REFUSAL_HINTS = re.compile(r"(don't have that information|do not have that information|could not|couldn't|no matching|"
                           r"not in the knowledge base|knowledge base is empty)", re.I)


def _numbers(text: str) -> set[int]:
    return {int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", text) if n.replace(",", "").isdigit()}


def _times(text: str) -> set[str]:
    return {f"{int(h):02d}:{m}" for h, m in TIME.findall(text)}


def _segments(draft: str) -> list[str]:
    segs = []
    for line in draft.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "---", ">", "_", "- _")) or line.endswith(":**") or line.endswith(":"):
            continue
        segs.extend(s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z*])", line) if s.strip())
    return segs


def validate(draft: str, book: SourceBook, facts: list[dict], state: dict, analyst: DataAnalyst | None) -> dict:
    issues: list[str] = []
    labels = {i["label"] for i in book.items}
    evidence = " ".join(i["text"] for i in book.items) + " " + " ".join(f["text"] for f in facts)
    c = state.get("constraints") or {}
    allowed_numbers = _numbers(evidence) | {v for v in (c.get("budget"), c.get("max_price")) if v}
    allowed_times = _times(evidence) | ({c["time"]} if c.get("time") else set())

    cited = {f"S{n}" for n in CITE.findall(draft)}
    bad = sorted(cited - labels)
    if bad:
        issues.append(f"cites unknown sources {', '.join(bad)}")

    uncited = [s for s in _segments(draft) if re.search(r"\d", s) and len(s) > 20 and not CITE.search(s)]
    if uncited:
        issues.append(f"{len(uncited)} factual sentence(s) without a citation, e.g. '{uncited[0][:80]}'")

    for m in MONEY.finditer(draft):
        value = int(m.group(1).replace(",", ""))
        if value not in allowed_numbers:
            issues.append(f"price ₹{value} is not in the sources")
            break
    for t in _times(draft):
        if t not in allowed_times:
            issues.append(f"time {t} is not in the sources")
            break

    if not labels and not facts and not REFUSAL_HINTS.search(draft):
        issues.append("answer has no supporting sources")

    it = state.get("itinerary")
    checks = {"stops_checked": 0, "stops_open": 0, "budget_ok": None}
    if it:
        for s in it["stops"]:
            if s["type"] != "attraction":
                continue
            checks["stops_checked"] += 1
            status = analyst.attraction_status(s["name"], it.get("day")) if analyst else None
            ok = True
            if status:
                ok = status.get("open_on_day") is not False and \
                    to_min(s["start"]) >= to_min(status["open_time"]) and to_min(s["end"]) <= to_min(status["close_time"])
            if ok:
                checks["stops_open"] += 1
            else:
                issues.append(f"{s['name']} is not open at {s['start']}-{s['end']} on {it.get('day')}")
        if it.get("budget"):
            checks["budget_ok"] = it["total"] <= it["budget"]
            if not checks["budget_ok"] and not re.search(r"over your|over budget|exceed", draft, re.I):
                issues.append("itinerary is over budget but the answer does not say so")

    return {"passed": not issues, "issues": issues, "checks": checks, "citations": len(cited)}
