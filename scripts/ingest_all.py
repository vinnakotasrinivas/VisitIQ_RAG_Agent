"""Ingest every sample document into ChromaDB and the table registry.

Usage:
    python scripts/ingest_all.py                    # ingest sample_data/valid
    python scripts/ingest_all.py --reset            # wipe the knowledge base first
    python scripts/ingest_all.py --include-invalid  # also show how invalid files are rejected
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import INVALID_SAMPLE_DIR, VALID_SAMPLE_DIR  # noqa: E402
from src.data.tables import TableRegistry  # noqa: E402
from src.ingestion.pipeline import ingest_file  # noqa: E402
from src.llm.groq_client import LLMClient  # noqa: E402
from src.vectordb.store import VectorStore  # noqa: E402


def ingest_folder(folder: Path, store: VectorStore, registry: TableRegistry, llm) -> list:
    reports = []
    for path in sorted(p for p in folder.iterdir() if p.is_file()):
        rep = ingest_file(path.name, path.read_bytes(), store, registry, llm)
        reports.append(rep)
        status = "ACCEPTED" if rep.accepted else "REJECTED"
        detail = f"{rep.chunks} chunks" + (f", tables: {', '.join(rep.tables)}" if rep.tables else "") \
            if rep.accepted else rep.error
        print(f"  [{status}] {path.name:32s} {detail}")
        for w in rep.warnings:
            print(f"             warning: {w}")
    return reports


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--include-invalid", action="store_true")
    args = parser.parse_args()

    if not VALID_SAMPLE_DIR.exists() or not any(VALID_SAMPLE_DIR.iterdir()):
        sys.exit("No sample documents found. Run: python scripts/generate_sample_docs.py")

    store, registry, llm = VectorStore(), TableRegistry(), LLMClient()
    if args.reset:
        store.reset()
        registry.clear()
        print("Knowledge base reset.")
    print(f"LLM: {'Groq ' + llm.model if llm.available else 'not configured (rule-based mode)'}")
    print(f"Ingesting {VALID_SAMPLE_DIR} ...")
    ingest_folder(VALID_SAMPLE_DIR, store, registry, llm)
    if args.include_invalid and INVALID_SAMPLE_DIR.exists():
        print(f"Ingesting {INVALID_SAMPLE_DIR} (expect rejections) ...")
        ingest_folder(INVALID_SAMPLE_DIR, store, registry, llm)
    stats = store.stats()
    print(f"\nKnowledge base: {stats['chunks']} chunks from {len(stats['sources'])} files")
    print(f"Structured tables: {', '.join(registry.kinds())}")


if __name__ == "__main__":
    main()
