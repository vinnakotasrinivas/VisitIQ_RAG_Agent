# T10 - Guardrails

**Goal**: block unsafe, off-topic and manipulative inputs, and make outputs safe and honest.

## Files
- `src/guardrails/policies.py`: patterns and refusal texts
- `src/guardrails/input_guard.py`: `check_input(query) -> GuardResult(allowed, category, message, clean_query, warnings)`
- `src/guardrails/output_guard.py`: `finalise(answer, state) -> str`
- `tests/test_guardrails.py`

## Input categories
`empty`, `too_long`, `injection`, `unsafe_illegal`, `medical`, `legal`, `other_city`, `off_topic`, `greeting` (help text),
`pii` (redact and continue), `safety_sensitive` (continue and add a note).

## Output rules
- Append "Check before you go: prices and timings change; confirm with the official site or venue." when a rupee amount or time appears.
- Append the safety note and emergency numbers (100 police, 108 ambulance, 112 all-in-one) for safety-sensitive queries.
- Redact PII; block system-prompt leakage.

## Verify
```powershell
pytest tests/test_guardrails.py -v
```

## Done when
- [ ] E4 to E7 are refused with the right category; PII is redacted.
