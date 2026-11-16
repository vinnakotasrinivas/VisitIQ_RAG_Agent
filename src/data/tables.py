"""Structured table registry used by the Data Analyst (deterministic filtering, no LLM)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd

from src.config import TABLES_DIR
from src.utils.logging import get_logger

log = get_logger("tables")

# Order matters: the first schema whose required columns are all present wins.
SCHEMAS: dict[str, set[str]] = {
    "attractions": {"name", "area", "open_time", "close_time", "closed_day", "ticket_indian_inr"},
    "restaurants": {"name", "cuisine", "area", "price_per_person_inr", "veg_options"},
    "events": {"date", "event_name", "area", "start_time"},
    "metro_lines": {"line", "station", "seq"},
    "metro_fares": {"stops_from", "stops_to", "fare_inr"},
    "airport_bus": {"route_code", "origin", "destination", "fare_inr"},
    "day_passes": {"pass_name", "price_inr"},
    "local_fares": {"mode", "base_fare_inr"},
}

NUMERIC = {
    "attractions": ["ticket_indian_inr", "ticket_foreign_inr", "visit_mins", "metro_distance_km", "rating"],
    "restaurants": ["price_per_person_inr", "rating"],
    "events": ["ticket_inr"],
    "metro_lines": ["seq", "peak_frequency_mins"],
    "metro_fares": ["stops_from", "stops_to", "fare_inr"],
    "airport_bus": ["frequency_mins", "fare_inr"],
    "day_passes": ["price_inr"],
    "local_fares": ["base_fare_inr", "base_km", "per_km_inr"],
}
TIME_COLS = {"open_time", "close_time", "start_time", "end_time", "first_departure", "last_departure", "first_train",
             "last_train"}


def detect_table_kind(df: pd.DataFrame) -> str | None:
    cols = set(df.columns)
    for kind, required in SCHEMAS.items():
        if required <= cols:
            return kind
    return None


def _to_hhmm(value) -> str:
    if isinstance(value, (datetime, time)):
        return value.strftime("%H:%M")
    s = str(value).strip()
    m = re.match(r"^(\d{1,2})[:.](\d{2})", s)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    m = re.match(r"^(\d{1,2})\s*(am|pm)$", s, re.IGNORECASE)
    if m:
        h = int(m.group(1)) % 12 + (12 if m.group(2).lower() == "pm" else 0)
        return f"{h:02d}:00"
    return s


def normalise(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object or str(df[col].dtype).startswith("str"):
            df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
    for col in NUMERIC.get(kind, []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in TIME_COLS & set(df.columns):
        df[col] = df[col].map(_to_hhmm)
    if "date" in df.columns:
        df["date"] = df["date"].map(lambda v: v.date().isoformat() if isinstance(v, datetime)
                                    else v.isoformat() if isinstance(v, date) else str(v)[:10])
    if "closed_day" in df.columns:
        df["closed_day"] = df["closed_day"].fillna("None").astype(str)
    if "veg_options" in df.columns:
        df["veg_options"] = df["veg_options"].fillna("Unknown").astype(str)
    return df


class TableRegistry:
    def __init__(self, directory: Path | str = TABLES_DIR):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, tuple[float, pd.DataFrame]] = {}

    @property
    def _manifest_path(self) -> Path:
        return self.dir / "manifest.json"

    def manifest(self) -> dict[str, dict]:
        if self._manifest_path.exists():
            try:
                return json.loads(self._manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def save(self, kind: str, df: pd.DataFrame, source: str, sheet: str | None = None) -> None:
        df = df.copy()
        df["_source"] = source
        df["_row"] = range(1, len(df) + 1)
        if sheet:
            df["_sheet"] = sheet
        df.to_csv(self.dir / f"{kind}.csv", index=False)
        man = self.manifest()
        man[kind] = {"source": source, "sheet": sheet, "rows": len(df)}
        self._manifest_path.write_text(json.dumps(man, indent=2), encoding="utf-8")
        self._cache.pop(kind, None)
        log.info("Registered table %s from %s (%d rows)", kind, source, len(df))

    def get(self, kind: str) -> pd.DataFrame | None:
        path = self.dir / f"{kind}.csv"
        if not path.exists():
            return None
        mtime = path.stat().st_mtime
        cached = self._cache.get(kind)
        if cached and cached[0] == mtime:
            return cached[1]
        df = normalise(pd.read_csv(path, dtype={"date": str}), kind)
        self._cache[kind] = (mtime, df)
        return df

    def kinds(self) -> list[str]:
        return sorted(p.stem for p in self.dir.glob("*.csv"))

    def remove_source(self, source: str) -> None:
        man = self.manifest()
        for kind, info in list(man.items()):
            if info.get("source") == source:
                (self.dir / f"{kind}.csv").unlink(missing_ok=True)
                man.pop(kind)
                self._cache.pop(kind, None)
        self._manifest_path.write_text(json.dumps(man, indent=2), encoding="utf-8")

    def clear(self) -> None:
        for p in self.dir.glob("*"):
            p.unlink(missing_ok=True)
        self._cache.clear()
