# T09 - Responder, Validator and the LangGraph workflow

**Goal**: a grounded, cited answer that is checked before the user sees it.

## Files
- `src/agents/responder.py`: `build_context(state)`, `respond(state, llm, feedback=None)`, `template_answer(state)`
- `src/agents/validator.py`: `validate(state) -> {passed, issues}`
- `src/agents/graph.py`: `build_graph()`, `run_query(query, deps) -> AgentState`
- `tests/test_graph_e2e.py`

## Responder
- The context is numbered blocks `[S1] (source, page/row) text` plus a `FACTS` block from the analyst and itinerary (each fact carries `[S#]`).
- System prompt: answer only from the context, cite `[S#]` after every factual sentence, say "I don't have that information" otherwise, and never invent prices or hours.
- With no LLM, `template_answer` renders the facts directly (always grounded).

## Validator checks
1. Every `[S#]` cited exists in the context.
2. Every sentence with a number, price or time has at least one citation.
3. Every rupee amount and clock time in the draft appears in the context or the computed facts.
4. Itinerary: each stop is open at its time (re-checked against the table) and the total is <= budget, or the answer states it is over budget.

Failure: the Responder retries once with the issues as feedback. A second failure is replaced by `template_answer` plus the note "Some details could not be verified".

## Graph
`input_guard -> (refuse | planner) -> retriever -> (analyst -> itinerary?) -> responder -> validator -> (responder | output_guard) -> END`

## Verify
```powershell
pytest tests/test_graph_e2e.py -v
```

## Done when
- [ ] A1, A2 and A3 pass end to end in degraded mode (no key) and in LLM mode (with a key).
