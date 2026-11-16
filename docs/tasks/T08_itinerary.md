# T08 - Itinerary Planner

**Goal**: a feasible, time-ordered day plan with an exact cost breakdown.

## Files
- `src/agents/itinerary.py`: `build_itinerary(constraints, analysis) -> dict`
- `tests/test_itinerary.py`

## Algorithm
1. Day window 09:30 to 21:30 (or the user's time window).
2. Morning: attractions open that day, in or near the area, ordered by rating; each takes `visit_mins` plus a travel buffer
   (15 min in the same area, 40 min otherwise). A stop is only placed if it is open at arrival and the visit ends before closing.
3. Lunch at 13:00 to 14:00: the top restaurant in the area that matches veg / budget and is open.
4. Afternoon: more attractions until about 1 hour before the evening event.
5. Evening: an event on that date / weekday (prefer the same area).
6. Costs: tickets (Indian or foreign rate), meal, event, local transport estimate (from `local_fares`).
7. Over budget: drop paid optional attractions (lowest rating first) until it fits; if it still does not fit, set `feasible=False`
   with the shortfall.

## Output
```python
{"day": "Friday", "date": "2026-10-30", "stops": [{"start": "09:30", "end": "10:30", "type": "attraction",
 "name": "Charminar", "cost": 25, "source": "attractions.csv", "row": 1}], "excluded": [{"name": "Chowmahalla Palace",
 "reason": "closed on Friday"}], "costs": {...}, "total": 1350, "budget": 2000, "feasible": True, "notes": [...]}
```

## Verify
```powershell
pytest tests/test_itinerary.py -v
```

## Done when
- [ ] A1 excludes the Friday-closed sites and the total is <= 2000.
- [ ] A 100-rupee budget returns `feasible=False`.
