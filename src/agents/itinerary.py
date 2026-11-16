"""Itinerary Planner agent: deterministic, time-ordered day plan with opening-hour checks and a cost breakdown."""
from __future__ import annotations

from src.agents.data_analyst import DataAnalyst, neighbours, to_hhmm, to_min
from src.agents.state import Constraints
from src.config import (DAY_END, DAY_START, LUNCH_MINS, LUNCH_START, OTHER_AREA_TRAVEL_MINS, SAME_AREA_TRAVEL_MINS)

MAX_MORNING, MAX_AFTERNOON = 3, 3
SHORT_RIDE_KM, LONG_RIDE_KM = 3.0, 8.0


def _travel(a: str | None, b: str | None) -> int:
    if not a or not b or a == b or b in neighbours(a):
        return SAME_AREA_TRAVEL_MINS
    return OTHER_AREA_TRAVEL_MINS


def _ticket(attr: dict, visitor: str) -> int:
    key = "ticket_foreign_inr" if visitor == "foreign" else "ticket_indian_inr"
    return int(attr.get(key) or 0)


def build_itinerary(c: Constraints, analysis: dict, analyst: DataAnalyst) -> dict:
    notes: list[str] = []
    day = c.day
    area = c.area or next((s["area"] for s in analysis.get("attraction_status", []) if s), None) or "Charminar"
    if not c.area:
        notes.append(f"No area was given, so the plan is centred on {area}.")
    budget = c.budget

    # --- candidate attractions -------------------------------------------------
    mentioned = [s for s in analysis.get("attraction_status", []) if s]
    excluded = list(analysis.get("excluded", []))
    for s in mentioned:
        if s.get("open_on_day") is False:
            excluded.append({"name": s["name"], "reason": f"closed on {day}s", "ref": s["ref"]})
    mentioned_open = [s for s in mentioned if s.get("open_on_day") is not False]
    pool = mentioned_open + [a for a in analysis.get("attractions", [])
                             if a["name"] not in {m["name"] for m in mentioned}
                             and a.get("category") != "Venue" and int(a.get("visit_mins") or 0) <= 300]
    mentioned_names = {m["name"] for m in mentioned_open}

    # --- transport estimate per ride ---------------------------------------------
    short_fare, fare_ref = analyst.auto_fare(SHORT_RIDE_KM)
    long_fare, _ = analyst.auto_fare(LONG_RIDE_KM)
    short_fare, long_fare = short_fare or 60, long_fare or 130

    # --- choose evening event and lunch with the budget in mind ------------------
    events = [e for e in (analysis.get("events") or {}).get("items", [])]
    est_fixed = 2 * long_fare + 3 * short_fare
    spend_cap = (budget - est_fixed) if budget else None
    event = None
    if events:
        near = [e for e in events if e["area"] in neighbours(area) or e["area"] == area] or events
        if spend_cap is not None:
            affordable = [e for e in near if int(e.get("ticket_inr") or 0) <= max(0, spend_cap) * 0.4]
            event = affordable[0] if affordable else min(near, key=lambda e: int(e.get("ticket_inr") or 0))
            if event is not near[0]:
                notes.append(f"Chose '{event['event_name']}' instead of '{near[0]['event_name']}' to fit the budget.")
        else:
            event = near[0]
    lunch_list = analyst.restaurants_for(area, c.veg, None, True, c.cuisine, at=LUNCH_START, limit=30)["items"]
    snack_places = ("Cafe", "Desserts", "Bakery", "Snacks", "Breakfast", "Street Food")
    lunch_list = sorted(lunch_list, key=lambda r: any(s in str(r["cuisine"]) for s in snack_places))
    lunch = None
    if lunch_list:
        if spend_cap is not None:
            affordable = [r for r in lunch_list if int(r["price_per_person_inr"]) <= max(0, spend_cap) * 0.3]
            lunch = affordable[0] if affordable else min(lunch_list, key=lambda r: int(r["price_per_person_inr"]))
        else:
            lunch = lunch_list[0]

    # --- schedule ----------------------------------------------------------------
    stops: list[dict] = []
    t, cur = to_min(DAY_START), area
    used: set[str] = set()
    skipped: list[dict] = []

    def try_place(attr: dict, deadline: int, first: bool) -> tuple[int, int] | None:
        arrive = t + (0 if first else _travel(cur, attr["area"]))
        o, cl = to_min(attr["open_time"]), to_min(attr["close_time"])
        if cl <= o:
            cl = 24 * 60 - 1
        if arrive < o:
            if o - arrive > 45:
                return None
            arrive = o
        end = arrive + int(attr.get("visit_mins") or 60)
        if end > cl or end > deadline:
            return None
        return arrive, end

    def add_attraction(attr: dict, start: int, end: int) -> None:
        nonlocal t, cur
        stops.append({"type": "attraction", "start": to_hhmm(start), "end": to_hhmm(end), "name": attr["name"],
                      "area": attr["area"], "cost": _ticket(attr, c.visitor_type), "open_time": attr["open_time"],
                      "close_time": attr["close_time"], "rating": attr.get("rating"), "ref": attr["ref"],
                      "mentioned": attr["name"] in mentioned_names})
        used.add(attr["name"])
        t, cur = end, attr["area"]

    lunch_at = to_min(LUNCH_START)
    for attr in pool:
        if sum(s["type"] == "attraction" for s in stops) >= MAX_MORNING or t >= lunch_at - 15:
            break
        slot = try_place(attr, lunch_at + 15, not stops)
        if slot:
            add_attraction(attr, *slot)

    if lunch:
        start = max(t + _travel(cur, lunch["area"]), lunch_at - 30)
        stops.append({"type": "meal", "start": to_hhmm(start), "end": to_hhmm(start + LUNCH_MINS),
                      "name": f"Lunch at {lunch['name']}", "area": lunch["area"], "cost": int(lunch["price_per_person_inr"]),
                      "detail": f"{lunch['cuisine']}, veg options: {lunch['veg_options']}, rating {lunch['rating']}",
                      "open_time": lunch["open_time"], "close_time": lunch["close_time"], "ref": lunch["ref"]})
        t, cur = start + LUNCH_MINS, lunch["area"]
    else:
        notes.append("No restaurant matching your filters is open at lunch time in this area.")

    deadline = to_min(DAY_END)
    if event:
        deadline = to_min(event["start_time"]) - _travel(cur, event["area"]) - 15
    afternoon = 0
    for attr in pool:
        if attr["name"] in used or afternoon >= MAX_AFTERNOON:
            continue
        slot = try_place(attr, deadline, False)
        if slot:
            add_attraction(attr, *slot)
            afternoon += 1
        elif attr["name"] in mentioned_names:
            skipped.append({"name": attr["name"], "reason": "does not fit the opening hours / time available"})

    if event:
        e_start = to_min(event["start_time"])
        if e_start - t > 75:
            stops.append({"type": "free", "start": to_hhmm(t + 15), "end": to_hhmm(e_start - 15), "name": "Free time",
                          "area": cur, "cost": 0, "detail": "Shopping, chai or rest before the evening event",
                          "ref": None})
        stops.append({"type": "event", "start": event["start_time"], "end": event["end_time"],
                      "name": event["event_name"], "area": event["area"], "cost": int(event.get("ticket_inr") or 0),
                      "detail": f"{event['venue']} ({event['category']})", "ref": event["ref"]})
    elif "event" in c.topics:
        notes.append("No evening event was found for that day in the events calendar.")

    # --- costs and budget fitting --------------------------------------------------
    def compute() -> dict:
        rides_short = sum(1 for a, b in zip(stops, stops[1:]) if b["type"] != "free" and _travel(a["area"], b["area"])
                          == SAME_AREA_TRAVEL_MINS and a["area"] != b["area"])
        rides_long = 2 + sum(1 for a, b in zip(stops, stops[1:]) if _travel(a["area"], b["area"]) == OTHER_AREA_TRAVEL_MINS)
        costs = {
            "tickets": sum(s["cost"] for s in stops if s["type"] == "attraction"),
            "food": sum(s["cost"] for s in stops if s["type"] == "meal"),
            "events": sum(s["cost"] for s in stops if s["type"] == "event"),
            "transport": rides_short * short_fare + rides_long * long_fare,
        }
        return {"costs": costs, "total": sum(costs.values()), "rides": {"short": rides_short, "long": rides_long}}

    summary = compute()
    if budget is not None and summary["total"] > budget:
        paid = sorted([s for s in stops if s["type"] == "attraction" and s["cost"] > 0 and not s["mentioned"]],
                      key=lambda s: (s["rating"] or 0))
        for s in paid:
            stops.remove(s)
            notes.append(f"Removed {s['name']} (ticket Rs {s['cost']}) to stay within the budget.")
            summary = compute()
            if summary["total"] <= budget:
                break
    feasible = budget is None or summary["total"] <= budget
    shortfall = 0 if feasible else summary["total"] - budget
    if not feasible:
        notes.append(f"Even the cheapest version of this plan costs Rs {summary['total']}, which is Rs {shortfall} over "
                     f"your Rs {budget} budget. Consider skipping paid entries, eating at an Irani cafe, or walking "
                     "between nearby sights.")

    stops.sort(key=lambda s: to_min(s["start"]))
    notes.append(f"Ticket prices use {'foreign national' if c.visitor_type == 'foreign' else 'Indian citizen'} rates.")
    notes.append(f"Transport is an auto-rickshaw estimate: {summary['rides']['long']} longer rides (about "
                 f"{LONG_RIDE_KM:.0f} km, Rs {long_fare}) and {summary['rides']['short']} short hops (about "
                 f"{SHORT_RIDE_KM:.0f} km, Rs {short_fare}), including getting to and from the area.")
    return {"day": day, "date": c.date, "area": area, "budget": budget, "stops": stops, "excluded": excluded,
            "skipped": skipped, "costs": summary["costs"], "total": summary["total"], "feasible": feasible,
            "shortfall": shortfall, "notes": notes, "transport_ref": fare_ref, "visitor_type": c.visitor_type}
