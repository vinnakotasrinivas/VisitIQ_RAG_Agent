# T05 - Upload relevance check

**Goal**: only Hyderabad travel and tourism content enters the knowledge base.

## Files
- `src/ingestion/relevance.py`: `check_relevance(text, filename, llm=None) -> RelevanceResult(relevant, score, reason)`
- `tests/test_relevance.py`

## Algorithm
1. Count hits for Hyderabad terms (hyderabad, charminar, golconda, hitech city, banjara hills, telangana, ...),
   tourism terms (visitor, ticket, attraction, metro, restaurant, festival, ...), other-city terms
   (bengaluru, mumbai, delhi, ...), and non-tourism terms (invoice, prescription, GST, patient, dosage ...).
2. Reject when other-city hits outnumber Hyderabad hits, when there are no Hyderabad hits, or when non-tourism hits dominate.
3. Accept with a clear margin. In the grey zone, ask the LLM for a JSON verdict `{relevant, reason}`; if the LLM is unavailable, accept only when score >= threshold.
4. The rejection message names the reason: "This looks like a pharmacy invoice, not Hyderabad travel content."

## Verify
```powershell
pytest tests/test_relevance.py -v
```

## Done when
- [ ] All 9 valid samples are accepted; `pharmacy_invoice.pdf` and `bengaluru_guide.pdf` are rejected.
