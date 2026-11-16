import os

import pandas as pd
import pytest

from src.data.tables import TableRegistry, _to_hhmm, detect_table_kind, normalise
from src.ingestion.loaders import load_file
from src.llm.groq_client import LLMClient
from src.utils.errors import LLMUnavailableError


def test_detect_all_kinds(valid_file):
    kinds = set()
    for name in ["attractions.csv", "restaurants.csv", "events_calendar.xlsx", "transport_timetable.xlsx"]:
        for t in load_file(*valid_file(name)).tables:
            kinds.add(detect_table_kind(t.df))
    assert kinds == {"attractions", "restaurants", "events", "metro_lines", "metro_fares", "airport_bus", "day_passes",
                     "local_fares"}


def test_unknown_table_returns_none():
    assert detect_table_kind(pd.DataFrame({"foo": [1], "bar": [2]})) is None


@pytest.mark.parametrize("raw,expected", [("9:30", "09:30"), ("17.30", "17:30"), ("5 pm", "17:00"), ("12am", "00:00")])
def test_time_normalisation(raw, expected):
    assert _to_hhmm(raw) == expected


def test_registry_roundtrip(tmp_path):
    reg = TableRegistry(tmp_path)
    df = normalise(pd.DataFrame({"name": ["X"], "cuisine": ["South Indian"], "area": ["Abids"],
                                 "price_per_person_inr": ["200"], "veg_options": ["Pure veg"]}), "restaurants")
    reg.save("restaurants", df, source="r.csv")
    got = reg.get("restaurants")
    assert got.loc[0, "price_per_person_inr"] == 200
    assert reg.manifest()["restaurants"]["source"] == "r.csv"
    reg.remove_source("r.csv")
    assert reg.get("restaurants") is None


def test_llm_without_key_is_unavailable():
    client = LLMClient(api_key="")
    assert not client.available
    with pytest.raises(LLMUnavailableError):
        client.chat([{"role": "user", "content": "hi"}])
    assert client.ping() is False


@pytest.mark.live
@pytest.mark.skipif(not os.getenv("GROQ_API_KEY") and not LLMClient().available, reason="GROQ_API_KEY not set")
def test_llm_live_ping():
    assert LLMClient().ping()
