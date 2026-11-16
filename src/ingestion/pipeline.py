"""End-to-end ingestion of one file: validate, load, relevance check, sanitise, chunk, embed, store, register tables."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.data.tables import TableRegistry, detect_table_kind, normalise
from src.ingestion.chunker import chunk_documents
from src.ingestion.loaders import load_file
from src.ingestion.relevance import check_relevance
from src.utils.errors import EmptyFileError, IrrelevantDocumentError, VisitIQError
from src.utils.logging import get_logger
from src.vectordb.store import VectorStore

log = get_logger("pipeline")


@dataclass
class IngestReport:
    name: str
    accepted: bool
    chunks: int = 0
    tables: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    error_type: str | None = None
    relevance: str = ""
    seconds: float = 0.0


def ingest_file(name: str, data: bytes, store: VectorStore, registry: TableRegistry, llm=None) -> IngestReport:
    start = time.perf_counter()
    report = IngestReport(name=name, accepted=False)
    try:
        loaded = load_file(name, data)
        rel = check_relevance(loaded.sample_text, loaded.name, llm)
        report.relevance = rel.reason
        if not rel.relevant:
            raise IrrelevantDocumentError(rel.reason)

        chunks, removed = chunk_documents(loaded.documents)
        if removed:
            report.warnings.append(f"Removed {len(removed)} instruction-like line(s) that looked like a prompt-injection "
                                   "attempt; the rest of the document was kept.")
        if not chunks:
            raise EmptyFileError(f"'{name}' has no usable text after cleaning.")

        store.delete_source(loaded.name)
        registry.remove_source(loaded.name)
        report.chunks = store.add(chunks)

        for table in loaded.tables:
            kind = detect_table_kind(table.df)
            label = f"sheet '{table.sheet}'" if table.sheet else "table"
            if kind:
                registry.save(kind, normalise(table.df, kind), source=loaded.name, sheet=table.sheet)
                report.tables.append(kind)
            else:
                report.warnings.append(f"The {label} has an unrecognised layout, so it is searchable but not used for "
                                       "exact filtering.")
        report.accepted = True
    except VisitIQError as exc:
        report.error = exc.user_message
        report.error_type = type(exc).__name__
        log.info("Rejected %s: %s", name, exc.user_message)
    except Exception as exc:  # never surface a stack trace to the user
        log.exception("Unexpected ingestion error for %s", name)
        report.error = f"Unexpected error while processing '{name}'. Details were written to logs/visitiq.log."
        report.error_type = type(exc).__name__
    report.seconds = round(time.perf_counter() - start, 2)
    return report
