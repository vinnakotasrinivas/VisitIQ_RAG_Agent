"""ChromaDB persistent vector store wrapper."""
from __future__ import annotations

import hashlib
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb  # noqa: E402
from chromadb.config import Settings  # noqa: E402

from src.config import CHROMA_DIR, COLLECTION_NAME, MIN_SIMILARITY, TOP_K  # noqa: E402
from src.ingestion.loaders import Document  # noqa: E402
from src.utils.errors import VectorStoreError  # noqa: E402
from src.utils.logging import get_logger  # noqa: E402
from src.vectordb.embeddings import embed  # noqa: E402

log = get_logger("vectordb")


def _clean_meta(meta: dict) -> dict:
    return {k: v for k, v in meta.items() if v is not None and isinstance(v, (str, int, float, bool))}


class VectorStore:
    def __init__(self, path: Path | str = CHROMA_DIR, collection: str = COLLECTION_NAME):
        self.path = Path(path)
        self.collection_name = collection
        try:
            self.path.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(self.path),
                                                    settings=Settings(anonymized_telemetry=False, allow_reset=True))
            self.col = self._collection()
        except Exception as exc:
            log.exception("Chroma init failed")
            raise VectorStoreError(detail=str(exc)) from exc

    def _collection(self):
        return self.client.get_or_create_collection(name=self.collection_name, metadata={"hnsw:space": "cosine"},
                                                    embedding_function=None)

    # --- write -------------------------------------------------------------
    def add(self, chunks: list[Document]) -> int:
        if not chunks:
            return 0
        ids, texts, metas = [], [], []
        for i, c in enumerate(chunks):
            key = f"{c.metadata.get('source')}|{c.metadata.get('sheet')}|{c.metadata.get('page')}|{c.metadata.get('row')}|{c.metadata.get('chunk')}|{i}"
            ids.append(hashlib.sha1(key.encode()).hexdigest())
            texts.append(c.text)
            metas.append(_clean_meta(c.metadata))
        vectors = embed(texts)
        for start in range(0, len(ids), 500):
            end = start + 500
            self.col.upsert(ids=ids[start:end], documents=texts[start:end], embeddings=vectors[start:end],
                            metadatas=metas[start:end])
        log.info("Upserted %d chunks", len(ids))
        return len(ids)

    def delete_source(self, source: str) -> None:
        try:
            self.col.delete(where={"source": source})
        except Exception:
            log.warning("Delete for source %s failed (may not exist)", source)

    def reset(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.col = self._collection()

    # --- read --------------------------------------------------------------
    def count(self) -> int:
        return self.col.count()

    def search(self, query: str, k: int = TOP_K, where: dict | None = None,
               min_similarity: float = MIN_SIMILARITY) -> list[dict]:
        if not query.strip() or self.count() == 0:
            return []
        try:
            res = self.col.query(query_embeddings=embed([query]), n_results=min(k, self.count()), where=where,
                                 include=["documents", "metadatas", "distances"])
        except Exception as exc:
            log.exception("Chroma query failed")
            raise VectorStoreError(detail=str(exc)) from exc
        hits = []
        for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            sim = round(1.0 - float(dist), 4)
            if sim >= min_similarity:
                hits.append({"text": text, "metadata": meta or {}, "similarity": sim})
        return hits

    def stats(self) -> dict:
        total = self.count()
        if total == 0:
            return {"chunks": 0, "sources": {}}
        metas = self.col.get(include=["metadatas"])["metadatas"]
        sources = Counter((m or {}).get("source", "unknown") for m in metas)
        return {"chunks": total, "sources": dict(sorted(sources.items()))}
