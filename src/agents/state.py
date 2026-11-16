"""Shared state and typed contracts for the LangGraph workflow."""
from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field

Intent = Literal["info_lookup", "data_filter", "itinerary", "transport"]


class Constraints(BaseModel):
    day: str | None = None                # "Friday"
    date: str | None = None               # ISO date
    area: str | None = None
    budget: int | None = None             # total trip budget (INR)
    max_price: int | None = None          # per-person price cap (INR)
    price_strict: bool = True             # "under 500" => < 500 ; "up to 500" => <= 500
    veg: bool = False
    cuisine: str | None = None
    time: str | None = None               # "14:00"
    time_window: str | None = None        # morning / afternoon / evening / night
    origin: str | None = None
    destination: str | None = None
    attractions: list[str] = Field(default_factory=list)
    visitor_type: Literal["indian", "foreign"] = "indian"
    topics: list[str] = Field(default_factory=list)  # lunch, dinner, breakfast, event, food, metro, ...


class PlannerOutput(BaseModel):
    intents: list[Intent] = Field(default_factory=lambda: ["info_lookup"])
    constraints: Constraints = Field(default_factory=Constraints)


class AgentState(TypedDict, total=False):
    query: str
    clean_query: str
    blocked: bool
    guard_category: str
    intents: list[str]
    constraints: dict
    retrieved: list[dict]
    analysis: dict
    itinerary: dict
    sources: list[dict]
    facts: list[dict]
    draft: str
    attempts: int
    validation: dict
    final_answer: str
    llm_used: bool
    warnings: Annotated[list[str], operator.add]
    trace: Annotated[list[dict], operator.add]
