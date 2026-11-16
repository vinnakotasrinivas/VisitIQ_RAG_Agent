# VisitIQ - Run Guide (task by task)

Work through the tasks in order. Each task spec in `docs/tasks/` lists its files, design and a "Done when" checklist.
Run every command from the project root with the venv activated.

```powershell
cd C:\path\to\VisitIQ_RAG_Agent
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
```

| Step | Task | Command to run | What you should see |
|------|------|----------------|---------------------|
| 1 | [T01 Environment](tasks/T01_environment.md) | `pip install -r requirements.txt` then `python -c "import src.config as c; print(c.MAX_FILE_MB)"` | `19` |
| 2 | [T02 Sample data](tasks/T02_sample_data.md) | `python scripts/generate_sample_docs.py` | 9 valid and 7 invalid files listed |
| 3 | [T03 Ingestion](tasks/T03_ingestion.md) | `pytest tests/test_validators.py tests/test_loaders.py -v` | All green |
| 4 | [T04 Vector DB](tasks/T04_vectordb.md) | `python scripts/ingest_all.py` | Per-file chunk counts, total chunks, tables registered |
| 5 | [T05 Relevance](tasks/T05_relevance.md) | `pytest tests/test_relevance.py -v` | Pharmacy invoice and Bengaluru guide rejected |
| 6 | [T06 LLM + tables](tasks/T06_llm_tables.md) | `python -c "from src.llm.groq_client import LLMClient; print(LLMClient().ping())"` | `True` (with a key) |
| 7 | [T07 Core agents](tasks/T07_core_agents.md) | `pytest tests/test_agents.py -v` | All green |
| 8 | [T08 Itinerary](tasks/T08_itinerary.md) | `pytest tests/test_itinerary.py -v` | All green |
| 9 | [T09 Graph](tasks/T09_responder_validator_graph.md) | `python -m src.agents.graph "Is Golconda Fort open on Mondays?"` | Cited answer plus agent trace |
| 10 | [T10 Guardrails](tasks/T10_guardrails.md) | `pytest tests/test_guardrails.py -v` | All green |
| 11 | [T11 UI](tasks/T11_ui.md) | `streamlit run app.py` | App at http://localhost:8501 |
| 12 | [T12 Docs + verify](tasks/T12_docs_verification.md) | `pytest -v` then `python scripts/smoke_test.py` then `python scripts/build_ppt.py` | All PASS; deck in `docs/` |

## Manual UI checklist (step 11)
1. Click **Load sample documents**; the Knowledge Base tab shows 9 files.
2. Upload `sample_data/invalid/sample.jpg`: you see "not supported".
3. Upload `sample_data/invalid/pharmacy_invoice.pdf`: you see "not Hyderabad travel content".
4. Run `python scripts/generate_sample_docs.py --oversize` and upload `oversize_20mb.txt`: you see "limit is 19 MB".
5. Click each happy-path sample prompt and check the citations, the itinerary table and the agent trace.
6. Click each edge-case prompt and check that it gets a polite refusal or a warning.
