# T07 - Planner, Retriever and Data Analyst

**Goal**: understand the question, fetch relevant passages and compute exact table facts.

## Files
- `src/agents/state.py`: `AgentState` TypedDict, `Constraints` Pydantic model
- `src/agents/planner.py`: `extract_constraints(query)` (rules) + `plan(query, llm)` -> intents, constraints
- `src/agents/retriever.py`: `retrieve(query, constraints, store)` -> chunks with `[S#]` labels
- `src/agents/data_analyst.py`: `analyse(constraints, intents, registry)` -> dict of results
- `tests/test_agents.py`

## Planner
- Intents: `info_lookup`, `data_filter`, `itinerary`, `transport`.
- Rule extraction: weekday, "today" / "tomorrow", date, budget (rupee sign, Rs, INR, "rupees"), "under N", area (known area list),
  vegetarian, cuisine, time window (morning / afternoon / evening / night / HH AM-PM), "from X to Y", named attraction, foreign visitor.
- The LLM returns JSON `{intents, constraints}` that is validated with Pydantic and merged (rules win on numbers).

## Data Analyst functions
| Function | Purpose |
|----------|---------|
| `attractions_for(day, area, time)` | Open on that day (closed_day != day) and in the area or its neighbours |
| `attraction_status(name, day, time)` | Open / closed with hours |
| `restaurants_for(area, veg, max_price, cuisine, time)` | Filtered and sorted by rating |
| `events_for(date or day, area, evening)` | Exact date if in the calendar, else weekly recurring events |
| `metro_route(origin, destination)` | Shortest path over metro lines (interchanges), stop count, fare slab, last-mile note |

## Verify
```powershell
pytest tests/test_agents.py -v
```

## Done when
- [ ] Planner extracts `day=Friday, area=Charminar, budget=2000` for A1.
- [ ] `metro_route("Hitech City", "Golconda Fort")` returns a Blue Line route plus a last-mile note.
