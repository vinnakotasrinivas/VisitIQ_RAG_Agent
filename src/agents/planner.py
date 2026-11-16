"""Planner agent: classify intents and extract constraints (rules first, LLM refinement second)."""
from __future__ import annotations

import json
import re
from datetime import date, timedelta

from pydantic import ValidationError

from src.agents.state import Constraints, PlannerOutput
from src.config import AREA_METRO, ATTRACTION_ALIASES, KNOWN_AREAS, WEEKDAYS
from src.utils.errors import LLMUnavailableError
from src.utils.logging import get_logger

log = get_logger("planner")

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
CUISINE_WORDS = [
    (r"\bbiryani\b", "Hyderabadi Biryani"), (r"\bsouth indian|dosa|idli\b", "South Indian"),
    (r"\bnorth indian\b", "North Indian"), (r"\bandhra\b", "Andhra Meals"), (r"\birani\b", "Irani Cafe"),
    (r"\bchinese\b", "Chinese"), (r"\b(dessert|ice ?cream|sweets?)\b", "Desserts"),
    (r"\b(street food|chaat)\b", "Street Food and Chaat"), (r"\bgujarati|thali\b", "Gujarati Thali"),
    (r"\bseafood\b", "Seafood"), (r"\b(barbecue|bbq)\b", "Barbecue"), (r"\bmandi\b", "Mandi (Arabian)"),
    (r"\b(bakery|cafe|coffee)\b", "Cafe"), (r"\bcontinental\b", "Continental"),
]
MONEY = r"(?:₹|rs\.?|inr)\s*([\d][\d,]*)|([\d][\d,]*)\s*(?:₹|rs\.?|inr|rupees?|/-)"
CAP_WORDS = r"(under|below|less than|cheaper than|within|up ?to|upto|max(?:imum)?|not more than|at most)"
STRICT_CAP = {"under", "below", "less than", "cheaper than"}

ITINERARY_RE = re.compile(r"\b(plan|itinerary|schedule|day plan|one day|full day|half day|spend (a|the|my|one) day|"
                          r"what (can|should) i do|things to do|how should i spend)\b", re.I)
TRANSPORT_RE = re.compile(r"\b(metro|bus|auto|cab|taxi|train|get there|get to|go to|reach|route|how do i get|"
                          r"how to get|airport|fare|travel from|from .+ to)\b", re.I)
DATA_RE = re.compile(r"\b(open|closed|close|timings?|hours|ticket|price|cost|fee|entry|restaurants?|eat|food|lunch|"
                     r"dinner|breakfast|events?|festival|show|which|list|under|below|cheap|veg|vegetarian|"
                     r"rating|best|recommend)\b", re.I)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("hi-tech", "hitech").replace("hi tech", "hitech")).strip()


def next_weekday(day: str, today: date) -> date:
    target = WEEKDAYS.index(day)
    return today + timedelta(days=(target - today.weekday()) % 7)


def _parse_date(q: str, today: date) -> date | None:
    m = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", q)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", q) or \
        re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b", q)
    if m:
        a, b = m.group(1), m.group(2)
        day_num, mon = (int(a), MONTHS[b[:3]]) if a.isdigit() else (int(b), MONTHS[a[:3]])
        for year in (today.year, today.year + 1):
            try:
                d = date(year, mon, day_num)
            except ValueError:
                return None
            if d >= today - timedelta(days=1):
                return d
    return None


def _parse_time(q: str) -> str | None:
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)", q)
    if m:
        h = int(m.group(1)) % 12 + (12 if m.group(3).startswith("p") else 0)
        return f"{h:02d}:{m.group(2) or '00'}"
    m = re.search(r"\bat\s+(\d{1,2}):(\d{2})\b", q)
    if m and int(m.group(1)) < 24:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    if re.search(r"\bmidnight\b", q):
        return "00:00"
    if re.search(r"\bnoon\b", q):
        return "12:00"
    return None


def _money(q: str) -> tuple[int | None, int | None, bool]:
    """Return (budget, max_price, strict)."""
    budget = max_price = None
    strict = True
    for m in re.finditer(MONEY, q):
        value = int((m.group(1) or m.group(2)).replace(",", ""))
        before = q[max(0, m.start() - 25):m.start()]
        around = q[max(0, m.start() - 30):m.end() + 25]
        cap = re.search(CAP_WORDS + r"\s*$", before.strip() + " ")
        cap = cap or re.search(CAP_WORDS + r"\W*$", before)
        if "budget" in around and not re.search(r"per (person|head)", around):
            budget = value
        elif cap or re.search(r"per (person|head|meal)", around):
            max_price = value
            strict = (cap.group(1) if cap else "under") in STRICT_CAP
        else:
            budget = value
    if max_price is None:
        m = re.search(CAP_WORDS + r"\s*([\d][\d,]*)\b", q)
        if m and not re.search(r"\b(km|kms|min|mins|minutes|hours?|people|persons)\b", q[m.end():m.end() + 8]):
            max_price = int(m.group(2).replace(",", ""))
            strict = m.group(1) in STRICT_CAP
    return budget, max_price, strict


def _find_place(fragment: str) -> str | None:
    frag = _norm(fragment)
    for alias, name in ATTRACTION_ALIASES.items():
        if alias in frag:
            return name
    for area in KNOWN_AREAS:
        if _norm(area) in frag:
            return area
    for st in set(AREA_METRO.values()):
        if _norm(st) in frag:
            return st
    return None


def extract_constraints(query: str, today: date | None = None, attraction_names: list[str] | None = None) -> Constraints:
    today = today or date.today()
    q = _norm(query)
    c = Constraints()

    # day / date
    d = _parse_date(q, today)
    if re.search(r"\btoday|tonight\b", q):
        d = today
    elif re.search(r"\btomorrow\b", q):
        d = today + timedelta(days=1)
    for wd in WEEKDAYS:
        if re.search(rf"\b{wd.lower()}s?\b|\b{wd.lower()[:3]}\b", q):
            c.day = wd
            break
    if re.search(r"\bweekend\b", q) and not c.day:
        c.day = "Saturday"
    if d:
        c.date = d.isoformat()
        c.day = c.day or WEEKDAYS[d.weekday()]
    elif c.day:
        c.date = next_weekday(c.day, today).isoformat()

    # money
    c.budget, c.max_price, c.price_strict = _money(q)

    # attractions
    found: list[str] = []
    for alias, name in ATTRACTION_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", q) and name not in found:
            found.append(name)
    for name in attraction_names or []:
        base = _norm(re.sub(r"\(.*?\)", "", name))
        if base and re.search(rf"\b{re.escape(base)}\b", q) and name not in found:
            found.append(name)
    c.attractions = found

    # origin / destination
    m = re.search(r"\bfrom\s+(?:the\s+)?([a-z0-9 .'-]{3,40}?)(?=\s+(?:to|by|on|and|via|in|for)\b|[?,.!]|$)", q)
    if m:
        c.origin = _find_place(m.group(1))
    m = re.search(r"\b(?:to|reach|get to|go to)\s+(?:the\s+)?([a-z0-9 .'-]{3,40}?)(?=\s+(?:from|by|on|and|via|in|for)\b|[?,.!]|$)", q)
    if m:
        dest = _find_place(m.group(1))
        if dest and dest != c.origin:
            c.destination = dest
    if not c.destination and c.origin and found:
        c.destination = found[0]

    # area (prefer "near/in/around X")
    m = re.search(r"\b(?:near|in|around|at|close to)\s+(?:the\s+)?([a-z0-9 .'-]{3,30})", q)
    near = _find_place(m.group(1)) if m else None
    if near in KNOWN_AREAS:
        c.area = near
    else:
        for area in KNOWN_AREAS:
            if re.search(rf"\b{re.escape(_norm(area))}\b", q) and _norm(area) != _norm(c.origin or ""):
                c.area = area
                break

    # food
    c.veg = bool(re.search(r"\b(veg|vegetarian|pure veg|vegan|jain)\b", q)) and not re.search(r"\bnon[- ]?veg", q)
    for pattern, cuisine in CUISINE_WORDS:
        if re.search(pattern, q):
            c.cuisine = cuisine
            break

    # time
    c.time = _parse_time(q)
    for w in ("morning", "afternoon", "evening", "night"):
        if re.search(rf"\b{w}\b", q):
            c.time_window = w
            break

    if re.search(r"\b(foreign(er|ers)?|foreign national|international (tourist|visitor)|from abroad|non[- ]indian)\b", q) \
            and not re.search(r"\bsim\b", q):
        c.visitor_type = "foreign"

    topics = []
    for t, pat in [("lunch", r"\blunch\b"), ("dinner", r"\bdinner\b"), ("breakfast", r"\bbreakfast\b"),
                   ("event", r"\b(event|events|show|festival|concert|qawwali|performance|tonight)\b"),
                   ("food", r"\b(restaurants?|eat|food|cuisine|biryani|veg|vegetarian|cafe|meal)\b"),
                   ("metro", r"\bmetro\b"), ("airport", r"\b(airport|rgia|shamshabad airport|flight)\b"),
                   ("hours", r"\b(open|closed|timings?|hours)\b"),
                   ("ticket", r"\b(ticket|entry fee|price|cost)\b")]:
        if re.search(pat, q):
            topics.append(t)
    c.topics = topics
    return c


def classify_intents(query: str, c: Constraints) -> list[str]:
    intents = ["info_lookup"]
    if ITINERARY_RE.search(query) or (c.budget and ("lunch" in c.topics or "event" in c.topics)):
        intents.append("itinerary")
    if DATA_RE.search(query) or c.attractions or c.max_price or c.veg or c.cuisine:
        intents.append("data_filter")
    if TRANSPORT_RE.search(query) and (c.origin or c.destination or {"metro", "airport"} & set(c.topics)):
        intents.append("transport")
    return intents


SYSTEM = (
    "You are the Planner of a Hyderabad tourist assistant. Classify the user's question and extract constraints. "
    "Intents: info_lookup (general facts from guides), data_filter (filter attractions/restaurants/events by day, area, "
    "price, veg), itinerary (a time-ordered day plan), transport (getting from A to B). Return ONLY JSON with keys "
    '"intents" (list) and "constraints" (object with optional keys: area, attractions, origin, destination, cuisine, '
    'veg, time_window, topics). Do not invent prices, dates or budgets.'
)


def plan(query: str, llm=None, today: date | None = None, attraction_names: list[str] | None = None) -> tuple[PlannerOutput, str]:
    """Return (PlannerOutput, method) where method is 'rules' or 'rules+llm'."""
    rules = extract_constraints(query, today, attraction_names)
    intents = classify_intents(query, rules)
    out = PlannerOutput(intents=intents, constraints=rules)
    if llm is None or not getattr(llm, "available", False):
        return out, "rules"
    try:
        raw = llm.chat([{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": f"Question: {query}\nRule-based draft: {out.model_dump_json()}"}],
                       json_mode=True, max_tokens=300)
        data = json.loads(raw)
        llm_out = PlannerOutput.model_validate({"intents": data.get("intents") or intents,
                                                "constraints": {**rules.model_dump(), **_safe_fields(data.get("constraints") or {})}})
    except (LLMUnavailableError, json.JSONDecodeError, ValidationError, TypeError) as exc:
        log.warning("LLM planner failed (%s); using rules", type(exc).__name__)
        return out, "rules"
    merged_intents = list(dict.fromkeys(["info_lookup", *intents, *llm_out.intents]))
    # numbers, dates and days always come from deterministic rules
    final = llm_out.constraints.model_copy(update={"budget": rules.budget, "max_price": rules.max_price,
                                                   "price_strict": rules.price_strict, "day": rules.day,
                                                   "date": rules.date, "time": rules.time,
                                                   "visitor_type": rules.visitor_type,
                                                   "attractions": list(dict.fromkeys(rules.attractions +
                                                                                     llm_out.constraints.attractions))})
    return PlannerOutput(intents=merged_intents, constraints=final), "rules+llm"


def _safe_fields(raw: dict) -> dict:
    """Only accept LLM values for descriptive fields, and only when they map to known places."""
    out: dict = {}
    for key in ("area", "origin", "destination"):
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            place = _find_place(val)
            if place:
                out[key] = place
    if isinstance(raw.get("attractions"), list):
        names = [_find_place(a) for a in raw["attractions"] if isinstance(a, str)]
        names = [n for n in names if n and n not in KNOWN_AREAS]
        if names:
            out["attractions"] = names
    if isinstance(raw.get("veg"), bool):
        out["veg"] = raw["veg"]
    if raw.get("time_window") in {"morning", "afternoon", "evening", "night"}:
        out["time_window"] = raw["time_window"]
    return {k: v for k, v in out.items() if v not in (None, "", [])}
