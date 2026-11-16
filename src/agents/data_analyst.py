"""Data Analyst agent: deterministic pandas filters over the structured tables (no LLM, no arithmetic hallucination)."""
from __future__ import annotations

import heapq
import math
import re
from datetime import date

import pandas as pd

from src.agents.state import Constraints
from src.config import AREA_METRO, AREA_NEIGHBOURS, WEEKDAYS
from src.data.tables import TableRegistry
from src.utils.logging import get_logger

log = get_logger("analyst")


# --- time helpers ----------------------------------------------------------------
def to_min(hhmm: str) -> int:
    h, m = str(hhmm).split(":")[:2]
    return int(h) * 60 + int(m)


def to_hhmm(minutes: int) -> str:
    minutes = max(0, min(minutes, 24 * 60 - 1))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def is_open_at(open_t: str, close_t: str, at: str) -> bool:
    o, c, t = to_min(open_t), to_min(close_t), to_min(at)
    return o <= t < c if c > o else (t >= o or t < c)


def ref(row: pd.Series) -> dict:
    return {"source": row.get("_source"), "sheet": row.get("_sheet") if isinstance(row.get("_sheet"), str) else None,
            "row": int(row.get("_row")) if pd.notna(row.get("_row")) else None}


def _records(df: pd.DataFrame, cols: list[str]) -> list[dict]:
    out = []
    for _, r in df.iterrows():
        rec = {c: (r[c].item() if hasattr(r[c], "item") else r[c]) for c in cols if c in df.columns}
        rec["ref"] = ref(r)
        out.append(rec)
    return out


def neighbours(area: str | None) -> list[str]:
    if not area:
        return []
    return AREA_NEIGHBOURS.get(area, [area])


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


class DataAnalyst:
    ATTR_COLS = ["name", "category", "area", "open_time", "close_time", "closed_day", "ticket_indian_inr",
                 "ticket_foreign_inr", "visit_mins", "nearest_metro", "metro_distance_km", "rating"]
    REST_COLS = ["name", "cuisine", "area", "price_per_person_inr", "veg_options", "rating", "open_time", "close_time"]
    EVENT_COLS = ["date", "day_of_week", "event_name", "category", "venue", "area", "start_time", "end_time",
                  "ticket_inr", "recurring"]

    def __init__(self, registry: TableRegistry):
        self.reg = registry

    # --- attractions -----------------------------------------------------------
    def find_attraction(self, name: str) -> pd.Series | None:
        df = self.reg.get("attractions")
        if df is None or not name:
            return None
        key = _norm(name)
        exact = df[df["name"].map(_norm) == key]
        if not exact.empty:
            return exact.iloc[0]
        part = df[df["name"].map(lambda n: key in _norm(n) or _norm(n) in key)]
        return part.iloc[0] if not part.empty else None

    def attraction_status(self, name: str, day: str | None, at: str | None = None) -> dict | None:
        row = self.find_attraction(name)
        if row is None:
            return None
        closed_day = str(row["closed_day"])
        rec = _records(row.to_frame().T, self.ATTR_COLS)[0]
        rec["open_on_day"] = None if not day else closed_day.lower() != day.lower()
        rec["day"] = day
        if at:
            rec["time"] = at
            rec["open_at_time"] = bool(rec["open_on_day"] is not False and is_open_at(row["open_time"], row["close_time"], at))
        return rec

    def attractions_for(self, day: str | None, area: str | None) -> tuple[list[dict], list[dict]]:
        df = self.reg.get("attractions")
        if df is None:
            return [], []
        if area:
            df = df[df["area"].isin(neighbours(area))]
        excluded = []
        if day:
            closed = df[df["closed_day"].str.lower() == day.lower()]
            excluded = [{"name": r["name"], "reason": f"closed on {day}s", "ref": ref(r)} for _, r in closed.iterrows()]
            df = df[df["closed_day"].str.lower() != day.lower()]
        df = df.sort_values("rating", ascending=False)
        return _records(df, self.ATTR_COLS), excluded

    # --- restaurants -----------------------------------------------------------
    def restaurants_for(self, area: str | None, veg: bool = False, max_price: int | None = None, strict: bool = True,
                        cuisine: str | None = None, at: str | None = None, limit: int = 8) -> dict:
        df = self.reg.get("restaurants")
        if df is None:
            return {"items": [], "total_matches": 0, "widened": False}

        def _filter(frame: pd.DataFrame, areas: list[str] | None) -> pd.DataFrame:
            if areas:
                frame = frame[frame["area"].isin(areas)]
            if veg:
                frame = frame[frame["veg_options"].isin(["Pure veg", "Yes"])]
            if max_price is not None:
                frame = frame[frame["price_per_person_inr"] < max_price] if strict else \
                    frame[frame["price_per_person_inr"] <= max_price]
            if cuisine:
                frame = frame[frame["cuisine"].str.contains(cuisine.split()[0], case=False, na=False)]
            if at:
                frame = frame[frame.apply(lambda r: is_open_at(r["open_time"], r["close_time"], at), axis=1)]
            return frame

        widened = False
        result = _filter(df, [area] if area else None)
        if area and len(result) < 3:
            result = _filter(df, neighbours(area))
            widened = len(neighbours(area)) > 1
        result = result.assign(_veg_rank=result["veg_options"].map({"Pure veg": 0, "Yes": 1}).fillna(2)) \
            .sort_values(["_veg_rank", "rating"] if veg else ["rating"], ascending=[True, False] if veg else [False])
        return {"items": _records(result.head(limit), self.REST_COLS), "total_matches": int(len(result)),
                "widened": widened}

    # --- events ----------------------------------------------------------------
    def events_for(self, on_date: str | None, day: str | None, area: str | None = None, evening: bool = False,
                   limit: int = 6) -> dict:
        df = self.reg.get("events")
        if df is None:
            return {"items": [], "note": None}
        note = None
        dated = df[df["recurring"] != "daily"]
        dates = sorted(dated["date"].dropna().unique())
        if on_date and dates and dates[0] <= on_date <= dates[-1]:
            sel = df[(df["date"] == on_date) | (df["recurring"] == "daily")].copy()
            sel["date"] = on_date
            sel["day_of_week"] = day or sel["day_of_week"]
        elif day:
            weekly = df[(df["recurring"] == "weekly") & (df["day_of_week"] == day)].drop_duplicates("event_name")
            sel = pd.concat([weekly, df[df["recurring"] == "daily"]])
            if on_date:
                note = (f"The events calendar covers {dates[0]} to {dates[-1]}; {on_date} is outside it, so only weekly "
                        f"and daily events usually held on {day}s are shown.") if dates else None
        else:
            sel = df[df["recurring"] == "daily"]
        if evening:
            sel = sel[sel["start_time"].map(lambda t: to_min(t) >= 16 * 60)]
        if area:
            near = neighbours(area)
            sel = sel.assign(_near=sel["area"].map(lambda a: 0 if a == area else 1 if a in near else 2))
            sel = sel.sort_values(["_near", "start_time"])
        else:
            sel = sel.sort_values("start_time")
        return {"items": _records(sel.head(limit), self.EVENT_COLS), "note": note}

    # --- transport -------------------------------------------------------------
    def resolve_station(self, place: str | None) -> tuple[str | None, dict | None]:
        """Map a place (station, area or attraction) to a metro station. Returns (station, attraction_record)."""
        if not place:
            return None, None
        lines = self.reg.get("metro_lines")
        stations = set(lines["station"]) if lines is not None else set()
        for st in stations:
            if _norm(st) == _norm(place):
                return st, None
        attr = self.find_attraction(place)
        if attr is not None and str(attr.get("nearest_metro")) in stations:
            return str(attr["nearest_metro"]), _records(attr.to_frame().T, self.ATTR_COLS)[0]
        if place in AREA_METRO:
            return AREA_METRO[place], None
        return None, None

    def _graph(self) -> dict:
        lines = self.reg.get("metro_lines")
        graph: dict[tuple, list[tuple]] = {}
        if lines is None:
            return graph
        for line, grp in lines.sort_values("seq").groupby("line"):
            sts = list(grp["station"])
            for a, b in zip(sts, sts[1:]):
                graph.setdefault((line, a), []).append(((line, b), 1))
                graph.setdefault((line, b), []).append(((line, a), 1))
        nodes = list(graph)
        by_station: dict[str, list[tuple]] = {}
        for n in nodes:
            by_station.setdefault(n[1], []).append(n)
        transfers = [(a, b) for group in by_station.values() for a in group for b in group if a != b]
        walk = [(n1, n2) for n1 in by_station.get("Parade Ground", []) for n2 in by_station.get("JBS Parade Ground", [])]
        for a, b in transfers + walk + [(b, a) for a, b in walk]:
            graph.setdefault(a, []).append((b, 4))  # a line change costs about 4 stops of time
        return graph

    def _fare(self, stops: int) -> tuple[int | None, dict | None]:
        fares = self.reg.get("metro_fares")
        if fares is None:
            return None, None
        hit = fares[(fares["stops_from"] <= stops) & (fares["stops_to"] >= stops)]
        if hit.empty:
            return None, None
        r = hit.iloc[0]
        return int(r["fare_inr"]), ref(r)

    def auto_fare(self, km: float) -> tuple[int | None, dict | None]:
        lf = self.reg.get("local_fares")
        if lf is None:
            return None, None
        hit = lf[lf["mode"].str.contains("Auto", case=False)]
        if hit.empty:
            return None, None
        r = hit.iloc[0]
        fare = float(r["base_fare_inr"]) + max(0.0, km - float(r["base_km"])) * float(r["per_km_inr"])
        return int(math.ceil(fare / 10.0) * 10), ref(r)

    def metro_route(self, origin: str | None, destination: str | None) -> dict | None:
        o_station, _ = self.resolve_station(origin)
        d_station, d_attr = self.resolve_station(destination)
        if not o_station or not d_station:
            return {"found": False, "reason": f"Could not map '{origin or '?'}' or '{destination or '?'}' to a metro station."}
        graph = self._graph()
        if not graph:
            return {"found": False, "reason": "Metro data is not loaded."}
        starts = [n for n in graph if n[1] == o_station]
        goals = {n for n in graph if n[1] == d_station}
        best = None
        for s in starts:
            dist, prev, heap = {s: 0}, {}, [(0, s)]
            while heap:
                cost, node = heapq.heappop(heap)
                if node in goals:
                    if best is None or cost < best[0]:
                        path = [node]
                        while path[-1] in prev:
                            path.append(prev[path[-1]])
                        best = (cost, list(reversed(path)))
                    break
                if cost > dist.get(node, math.inf):
                    continue
                for nxt, w in graph.get(node, []):
                    nc = cost + w
                    if nc < dist.get(nxt, math.inf):
                        dist[nxt], prev[nxt] = nc, node
                        heapq.heappush(heap, (nc, nxt))
        if best is None:
            return {"found": False, "reason": f"No metro path between {o_station} and {d_station}."}
        path = best[1]
        legs, stops_total = [], 0
        for node in path:
            if legs and legs[-1]["line"] == node[0]:
                legs[-1]["to"] = node[1]
                legs[-1]["stops"] += 1
                stops_total += 1
            elif not legs or legs[-1]["to"] != node[1] or legs[-1]["line"] != node[0]:
                legs.append({"line": node[0], "from": node[1], "to": node[1], "stops": 0})
        legs = [leg for leg in legs if leg["stops"] > 0]
        lines_df = self.reg.get("metro_lines")
        for leg in legs:
            grp = lines_df[lines_df["line"] == leg["line"]].sort_values("seq")
            seq = dict(zip(grp["station"], grp["seq"]))
            terminal = grp.iloc[-1]["station"] if seq[leg["to"]] > seq[leg["from"]] else grp.iloc[0]["station"]
            leg["towards"] = terminal
            r = grp[grp["station"] == leg["from"]].iloc[0]
            leg["ref"] = ref(r)
            leg["first_train"], leg["last_train"] = r.get("first_train"), r.get("last_train")
        fare, fare_ref = self._fare(stops_total)
        result = {"found": True, "origin": origin, "destination": destination, "from_station": o_station,
                  "to_station": d_station, "legs": legs, "stops": stops_total, "changes": max(0, len(legs) - 1),
                  "fare_inr": fare, "fare_ref": fare_ref}
        if d_attr and float(d_attr.get("metro_distance_km") or 0) > 0.8:
            km = float(d_attr["metro_distance_km"])
            auto, auto_ref = self.auto_fare(km)
            result["last_mile"] = {"km": km, "auto_fare_inr": auto, "ref": d_attr["ref"], "fare_ref": auto_ref,
                                   "to": d_attr["name"]}
        return result

    def airport_buses(self, place: str | None) -> dict:
        df = self.reg.get("airport_bus")
        if df is None:
            return {"items": [], "place": place}
        if place:
            key = _norm(place)
            match = df[df.apply(lambda r: key in _norm(r["destination"]) or key in _norm(r["via"]), axis=1)]
            if not match.empty:
                df = match
        cols = ["route_code", "origin", "destination", "via", "first_departure", "last_departure", "frequency_mins", "fare_inr"]
        return {"items": _records(df.head(6), cols), "place": place}

    # --- orchestration -----------------------------------------------------------
    def analyse(self, c: Constraints, intents: list[str]) -> dict:
        out: dict = {}
        day = c.day
        if c.attractions:
            statuses = [self.attraction_status(a, day, c.time) for a in c.attractions]
            out["attraction_status"] = [s for s in statuses if s]
        wants_food = bool({"food", "lunch", "dinner", "breakfast"} & set(c.topics)) or c.veg or c.cuisine or c.max_price
        if "itinerary" in intents or (c.area and not wants_food and not c.attractions and "event" not in c.topics
                                      and "transport" not in intents):
            items, excluded = self.attractions_for(day, c.area)
            out["attractions"] = items[:12]
            out["excluded"] = excluded
        if wants_food and "itinerary" not in intents:
            area = c.area or (out.get("attraction_status") or [{}])[0].get("area")
            out["restaurants"] = self.restaurants_for(area, c.veg, c.max_price, c.price_strict, c.cuisine, c.time)
            out["restaurants"]["filters"] = {"area": area, "veg": c.veg, "max_price": c.max_price,
                                             "strict": c.price_strict, "cuisine": c.cuisine}
        if "event" in c.topics or "itinerary" in intents:
            evening = c.time_window in {"evening", "night"} or "itinerary" in intents or "evening" in " ".join(c.topics)
            out["events"] = self.events_for(c.date, day, c.area, evening=evening)
        if "airport" in c.topics:
            out["airport_bus"] = self.airport_buses(c.destination or c.area or c.origin)
        elif "transport" in intents and (c.origin or c.destination):
            dest = c.destination or (c.attractions[0] if c.attractions else c.area)
            out["route"] = self.metro_route(c.origin or c.area, dest)
        out["day"], out["date"] = day, c.date
        return out


def weekday_of(iso: str) -> str:
    return WEEKDAYS[date.fromisoformat(iso).weekday()]
