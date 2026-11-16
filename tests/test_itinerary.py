from datetime import date

import pytest

from src.agents.data_analyst import DataAnalyst, to_min
from src.agents.itinerary import build_itinerary
from src.agents.planner import classify_intents, extract_constraints
from tests.test_agents import registry  # noqa: F401  (shared fixture)

TODAY = date(2026, 10, 26)


@pytest.fixture(scope="module")
def analyst(registry):  # noqa: F811
    return DataAnalyst(registry)


def _plan(analyst, query):
    names = list(analyst.reg.get("attractions")["name"])
    c = extract_constraints(query, TODAY, names)
    intents = classify_intents(query, c)
    analysis = analyst.analyse(c, intents)
    return c, build_itinerary(c, analysis, analyst)


A1 = "I have one day near Charminar on a Friday with a ₹2,000 budget. Plan my day with lunch and an evening event."


def test_a1_within_budget_and_ordered(analyst):
    c, it = _plan(analyst, A1)
    assert it["feasible"] and it["total"] <= 2000
    starts = [to_min(s["start"]) for s in it["stops"]]
    assert starts == sorted(starts)
    types = [s["type"] for s in it["stops"]]
    assert "meal" in types and types[-1] == "event"
    assert it["total"] == sum(it["costs"].values())


def test_a1_excludes_friday_closures(analyst):
    _, it = _plan(analyst, A1)
    names = {s["name"] for s in it["stops"]}
    assert "Chowmahalla Palace" not in names and "Salar Jung Museum" not in names
    assert {"Chowmahalla Palace", "Salar Jung Museum"} <= {e["name"] for e in it["excluded"]}


def test_every_attraction_open_during_visit(analyst):
    _, it = _plan(analyst, A1)
    for s in it["stops"]:
        if s["type"] == "attraction":
            assert to_min(s["start"]) >= to_min(s["open_time"])
            assert to_min(s["end"]) <= to_min(s["close_time"])


def test_tiny_budget_infeasible(analyst):
    _, it = _plan(analyst, "Plan a full day near Charminar on Saturday with 100 rupees")
    assert not it["feasible"] and it["shortfall"] > 0
    assert any("over" in n for n in it["notes"])


def test_foreign_rates(analyst):
    _, indian = _plan(analyst, "Plan my Saturday near Charminar with lunch")
    _, foreign = _plan(analyst, "I am a foreign national. Plan my Saturday near Charminar with lunch")
    assert foreign["costs"]["tickets"] > indian["costs"]["tickets"]


def test_veg_lunch(analyst):
    _, it = _plan(analyst, "Plan a vegetarian day in Banjara Hills on Sunday with lunch")
    meal = next(s for s in it["stops"] if s["type"] == "meal")
    assert "Pure veg" in meal["detail"] or "Yes" in meal["detail"]
