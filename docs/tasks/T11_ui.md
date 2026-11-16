# T11 - Streamlit UI

**Goal**: a self-explanatory interface that shows what the system does and why.

## Files
- `app.py`, `.streamlit/config.toml`

## Layout
| Area | Contents |
|------|----------|
| Header | Title, one-line description, status chips (LLM mode, documents, chunks) |
| Sidebar | "What is VisitIQ?", "How it works" (5 steps), an uploader labelled with allowed types and the 19 MB limit, "Load sample documents" button, "Reset knowledge base" button |
| Tab "Ask VisitIQ" | Sample prompt buttons (happy path and edge cases), chat with citations, expanders "Sources used", "Agent trace" and "Itinerary" table |
| Tab "Knowledge Base" | Ingested files, chunk counts, recognised tables, upload results log |
| Tab "About & Limitations" | Architecture summary, guardrails, limitations |

The uploader does not restrict file types itself, so the app's own validator can show its friendly error for JPG / ZIP.
`server.maxUploadSize = 25` lets a 20 MB file reach the validator.

## Verify
```powershell
streamlit run app.py
```
Upload the valid and invalid samples, then click each sample prompt.

## Done when
- [ ] Every label explains itself; errors appear as readable messages, never as stack traces.
