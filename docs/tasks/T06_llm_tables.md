# T06 - Groq client and table registry

**Goal**: a resilient LLM wrapper, plus structured tables the analyst can query.

## Files
- `src/llm/groq_client.py`: `LLMClient.chat(messages, json_mode=False, temperature=0.1, max_tokens=900)`, `.available`, `.ping()`
- `src/data/tables.py`: `detect_table_kind(df)`, `normalise(df, kind)`, `TableRegistry.save(kind, df)`, `.get(kind)`, `.kinds()`
- `tests/test_tables.py`

## LLM behaviour
| Situation | Behaviour |
|-----------|-----------|
| No `GROQ_API_KEY` | `available = False`; the app runs in degraded mode and the sidebar says so |
| Rate limit / connection / timeout | 3 attempts, backoff 1 s, 2 s, 4 s |
| Primary model fails | Retry once on `GROQ_FALLBACK_MODEL` |
| Still failing | Raise `LLMUnavailableError`; callers fall back to rules / templates |

## Table registry
Tables are persisted as CSV under `vectordb/tables/<kind>.csv`, so they survive restarts and are reset together with Chroma.

## Verify
```powershell
python -c "from src.llm.groq_client import LLMClient; c=LLMClient(); print(c.available, c.ping())"
pytest tests/test_tables.py -v
```

## Done when
- [ ] `ping()` returns True with a valid key.
- [ ] All 8 table kinds are detected from the sample files.
