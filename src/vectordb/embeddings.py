"""HuggingFace sentence-transformer embeddings (local, free)."""
from __future__ import annotations

import os
from functools import lru_cache

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

from src.config import EMBED_MODEL  # noqa: E402
from src.utils.errors import VectorStoreError  # noqa: E402
from src.utils.logging import get_logger  # noqa: E402

log = get_logger("embeddings")


@lru_cache(maxsize=1)
def get_model():
    try:
        from sentence_transformers import SentenceTransformer
        from transformers.utils import logging as hf_logging
        hf_logging.disable_progress_bar()
        model = SentenceTransformer(EMBED_MODEL, device="cpu")
        log.info("Loaded embedding model %s", EMBED_MODEL)
        return model
    except Exception as exc:
        log.exception("Embedding model load failed")
        raise VectorStoreError(
            f"Could not load the embedding model '{EMBED_MODEL}'. The first run needs internet access to download it "
            "(about 90 MB); afterwards it is cached.", detail=str(exc)) from exc


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = get_model().encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()
