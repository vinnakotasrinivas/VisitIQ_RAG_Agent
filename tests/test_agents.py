from datetime import date

import pytest

from src.agents.data_analyst import DataAnalyst
from src.agents.planner import classify_intents, extract_constraints, plan
from src.data.tables import TableRegistry, detect_table_kind, normalise
from src.ingestion.loaders import load_file

TODAY = date(2026, 10, 26)  # a Monday


@pytest.fixture(scope="module")
def registry(tmp_path_factory):
    from src.config import VALID_SAMPLE_DIR
    reg = TableRegistry(tmp_path_factory.mktemp("tables"))
    for name in ["attractions.csv", "restaurants.csv", "events_calendar.xlsx", "transport_timetable.xlsx"]:
        loaded = load_file(name, (VALID_SAMPLE_DIR / name).read_bytes())
        for t in loaded.tables:
            kind = detect_table_kind(t.df)
            reg.save(kind, normalise(t.df, kind), source=name, sheet=t.sheet)
    return reg


@pytest.fixture(scope="module")
def analyst(registry):
    return DataAnalyst(registry)


def test_planner_a1():
    c = extract_constraints("I have one day near Charminar on a Friday with a ₹2,000 budget. Plan my day with lunch "
                            "and an evening event.", TODAY, ["Charminar"])
    assert (c.day, c.area, c.budget, c.date) == ("Friday", "Charminar", 2000, "2026-10-30")
    assert {"lunch", "event"} <= set(c.topics)
    assert "itinerary" in classify_intents("Plan my day", c)


def test_planner_a2_origin_destination():
    c = extract_constraints("Is Golconda Fort open on Mondays, and how do I get there by metro from Hitech City?", TODAY)
    assert c.day == "Monday" and c.origin == "Hitech City" and c.destination == "Golconda Fort"
    assert "transport" in classify_intents("how do I get there by metro from Hitech City", c)


def test_planner_a3_price_cap():
    c = extract_constraints("Which vegetarian restaurants near Banjara Hills cost under ₹500 per person?", TODAY)
    assert c.veg and c.area == "Banjara Hills" and c.max_price == 500 and c.price_strict and c.budget is None


@pytest.mark.parametrize("text,budget", [("budget of Rs 1500", 1500), ("with 100 rupees", 100), ("INR 3,000 budget", 3000)])
def test_budget_variants(text, budget):
    assert extract_constraints(f"Plan a day in Hyderabad {text}", TODAY).budget == budget


def test_up_to_is_inclusive():
    c = extract_constraints("restaurants in Abids up to 300 per person", TODAY)
    assert c.max_price == 300 and not c.price_strict


def test_time_and_today():
    c = extract_constraints("Can I visit Charminar at 2 AM today?", TODAY)
    assert c.time == "02:00" and c.date == TODAY.isoformat() and c.day == "Monday"


def test_non_veg_not_veg():
    assert not extract_constraints("non-veg biryani near Charminar", TODAY).veg


def test_plan_without_llm_uses_rules():
    out, method = plan("Is Golconda Fort open on Mondays?", llm=None, today=TODAY)
    assert method == "rules" and "data_filter" in out.intents


def test_golconda_open_monday(analyst):
    s = analyst.attraction_status("Golconda Fort", "Monday")
    assert s["open_on_day"] is True and s["open_time"] == "09:00" and s["ref"]["source"] == "attractions.csv"


def test_salar_jung_closed_friday(analyst):
    assert analyst.attraction_status("Salar Jung Museum", "Friday")["open_on_day"] is False


def test_charminar_closed_at_2am(analyst):
    assert analyst.attraction_status("Charminar", None, "02:00")["open_at_time"] is False


def test_friday_exclusions_near_charminar(analyst):
    items, excluded = analyst.attractions_for("Friday", "Charminar")
    names = {e["name"] for e in excluded}
    assert {"Chowmahalla Palace", "Salar Jung Museum"} <= names
    assert all(i["closed_day"] != "Friday" for i in items)


def test_veg_restaurants_under_500(analyst):
    res = analyst.restaurants_for("Banjara Hills", veg=True, max_price=500, strict=True)
    assert res["items"]
    for r in res["items"]:
        assert r["price_per_person_inr"] < 500 and r["veg_options"] in {"Pure veg", "Yes"}


def test_metro_route_hitech_to_golconda(analyst):
    r = analyst.metro_route("Hitech City", "Golconda Fort")
    assert r["found"] and r["to_station"] == "Jubilee Hills Check Post" and r["stops"] == 4
    assert r["legs"][0]["line"] == "Blue Line" and r["fare_inr"] == 18
    assert r["last_mile"]["km"] == 8.0


def test_metro_route_with_interchange(analyst):
    r = analyst.metro_route("Hitech City", "Charminar")
    assert r["found"] and r["changes"] >= 1
    assert {leg["line"] for leg in r["legs"]} >= {"Blue Line", "Red Line"}


def test_events_on_friday(analyst):
    ev = analyst.events_for("2026-10-30", "Friday", "Charminar", evening=True)
    assert ev["items"][0]["area"] == "Charminar"


def test_events_outside_calendar_fall_back_to_weekly(analyst):
    ev = analyst.events_for("2030-01-04", "Friday", "Charminar", evening=True)
    assert ev["items"] and ev["note"]
