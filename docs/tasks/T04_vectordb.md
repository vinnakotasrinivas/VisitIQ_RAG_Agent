# T04 - Embeddings, ChromaDB and the ingest script

**Goal**: persist chunk embeddings and retrieve them by semantic similarity.

## Files
- `src/vectordb/embeddings.py`: cached `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")`, normalised vectors
- `src/vectordb/store.py`: `VectorStore.add(chunks)`, `.search(query, k, where)`, `.delete_source(name)`, `.stats()`, `.reset()`
- `src/ingestion/pipeline.py`: `ingest_file(name, data) -> IngestReport`
- `scripts/ingest_all.py`: ingests everything in `sample_data/valid`
- `tests/test_vectordb.py`

## Design
- `chromadb.PersistentClient(path="vectordb/chroma_store")`, collection `visitiq_hyderabad`, `hnsw:space=cosine`.
- Chunk id = `sha1(source + index)`; ingesting a source deletes its old chunks first (idempotent).
- `similarity = 1 - cosine_distance`; results below `MIN_SIMILARITY` (0.25) are dropped.

## Verify
```powershell
python scripts/ingest_all.py
python -c "from src.vectordb.store import VectorStore; print(VectorStore().search('Charminar opening hours', k=3))"
pytest tests/test_vectordb.py -v
```

## Done when
- [ ] Every valid sample file is ingested and the stats show the chunk count.
- [ ] "dress code mosque" returns the safety advisory as the top hit.
