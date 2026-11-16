# T01 - Environment and project skeleton

**Goal**: a reproducible Python 3.12 environment and the folder layout every later task builds on.

## Files
- `requirements.txt`, `.env`, `.env.example`, `.gitignore`, `.streamlit/config.toml`
- `src/__init__.py` and sub-packages `ingestion`, `vectordb`, `data`, `llm`, `agents`, `guardrails`, `utils`
- `src/config.py`, `src/utils/errors.py`, `src/utils/logging.py`

## Steps
1. Create the venv: `py -3.12 -m venv .venv` (or `uv venv .venv --python 3.12 --seed`).
2. Activate: `.\.venv\Scripts\Activate.ps1` (Windows) / `source .venv/bin/activate` (macOS/Linux).
3. `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and set `GROQ_API_KEY`.
5. `config.py` loads `.env` and defines: `MAX_FILE_MB = 19`, `ALLOWED_EXTENSIONS`, `EMBED_MODEL`, `CHROMA_DIR`,
   `COLLECTION_NAME`, `TOP_K`, `MIN_SIMILARITY`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, Groq model names, `AREA_NEIGHBOURS`.
6. `errors.py` defines `VisitIQError(user_message)` and its subclasses.
7. `logging.py` returns a logger that writes to the console and `logs/visitiq.log` (rotating).

## Verify
```powershell
python -c "import src.config as c; print(c.MAX_FILE_MB, c.EMBED_MODEL)"
```

## Done when
- [ ] The venv runs Python 3.12 and all packages import.
- [ ] `.env` exists with `GROQ_API_KEY`.
- [ ] The config command prints `19 sentence-transformers/all-MiniLM-L6-v2`.
