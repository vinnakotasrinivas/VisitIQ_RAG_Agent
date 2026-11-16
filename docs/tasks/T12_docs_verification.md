# T12 - README, architecture deck and verification

**Goal**: complete documentation and proof that everything works.

## Files
- `README.md`: overview, setup, step-by-step run guide, architecture, agent roles, sample prompts (happy and edge),
  troubleshooting, deployment (Streamlit Community Cloud), limitations, challenges
- `scripts/build_ppt.py` -> `docs/VisitIQ_Architecture.pptx` and `docs/architecture.png`
- `scripts/smoke_test.py`: runs every acceptance case and prints a PASS / FAIL table

## Verify
```powershell
python scripts/build_ppt.py
pytest -v
python scripts/smoke_test.py
streamlit run app.py
```

## Done when
- [ ] All tests pass and the smoke test reports every case as PASS.
- [ ] The deck has 6-7 visual slides (architecture, ingestion, agents, guardrails, limitations).
