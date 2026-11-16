"""Parse validated files into text `Document`s (for embedding) and DataFrames (for the table registry)."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.config import MAX_TABLE_ROWS
from src.ingestion.validators import validate_file
from src.utils.errors import CorruptFileError, EmptyFileError, FileValidationError
from src.utils.logging import get_logger

log = get_logger("loaders")


@dataclass
class Document:
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class LoadedTable:
    sheet: str | None
    df: pd.DataFrame


@dataclass
class LoadedFile:
    name: str
    doc_type: str
    documents: list[Document]
    tables: list[LoadedTable] = field(default_factory=list)

    @property
    def sample_text(self) -> str:
        """Representative text for the relevance check (first ~6,000 characters)."""
        out, total = [], 0
        for d in self.documents:
            out.append(d.text)
            total += len(d.text)
            if total > 6000:
                break
        return "\n".join(out)[:6000]


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise CorruptFileError("The text encoding could not be recognised. Please save the file as UTF-8.")


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_") or f"col_{i}"
                  for i, c in enumerate(df.columns)]
    return df.reset_index(drop=True)


def row_to_text(label: str, row: pd.Series) -> str:
    parts = [f"{col}: {val}" for col, val in row.items() if pd.notna(val) and str(val).strip() != ""]
    return f"{label} | " + " | ".join(parts)


def _table_documents(name: str, doc_type: str, df: pd.DataFrame, sheet: str | None) -> list[Document]:
    label = Path(name).stem if sheet is None else f"{Path(name).stem} / {sheet}"
    docs = []
    for i, row in df.iterrows():
        docs.append(Document(row_to_text(label, row), {"source": name, "doc_type": doc_type, "sheet": sheet,
                                                         "row": int(i) + 1}))
    return docs


def load_pdf(name: str, data: bytes) -> LoadedFile:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise CorruptFileError(f"'{name}' is password protected. Please upload an unlocked PDF.") from exc
        pages = [(i + 1, (p.extract_text() or "").strip()) for i, p in enumerate(reader.pages)]
    except FileValidationError:
        raise
    except (PdfReadError, ValueError, KeyError, OSError) as exc:
        raise CorruptFileError(f"'{name}' could not be read; the PDF may be damaged.") from exc
    docs = [Document(text, {"source": name, "doc_type": "pdf", "page": num}) for num, text in pages if text]
    if not docs:
        raise EmptyFileError(f"'{name}' has no extractable text. Scanned (image-only) PDFs are not supported.")
    return LoadedFile(name, "pdf", docs)


def load_txt(name: str, data: bytes) -> LoadedFile:
    text = _decode(data).replace("\r\n", "\n").strip()
    if not text:
        raise EmptyFileError(f"'{name}' is empty.")
    return LoadedFile(name, "txt", [Document(text, {"source": name, "doc_type": "txt", "page": 1})])


def _check_rows(name: str, df: pd.DataFrame, sheet: str | None = None) -> None:
    if len(df) > MAX_TABLE_ROWS:
        where = f" (sheet '{sheet}')" if sheet else ""
        raise FileValidationError(f"'{name}'{where} has {len(df):,} rows; the limit is {MAX_TABLE_ROWS:,} rows.")


def load_csv(name: str, data: bytes) -> LoadedFile:
    text = _decode(data)
    try:
        df = pd.read_csv(io.StringIO(text))
    except pd.errors.EmptyDataError as exc:
        raise EmptyFileError(f"'{name}' has no data.") from exc
    except pd.errors.ParserError as exc:
        raise CorruptFileError(f"'{name}' is not a well-formed CSV (inconsistent columns).") from exc
    df = _clean_columns(df)
    if df.empty:
        raise EmptyFileError(f"'{name}' has column headers but no data rows.")
    _check_rows(name, df)
    return LoadedFile(name, "csv", _table_documents(name, "csv", df, None), [LoadedTable(None, df)])


def load_xlsx(name: str, data: bytes) -> LoadedFile:
    try:
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, engine="openpyxl")
    except Exception as exc:  # openpyxl raises many different types for damaged files
        raise CorruptFileError(f"'{name}' could not be opened as an Excel workbook.") from exc
    docs, tables = [], []
    for sheet, df in sheets.items():
        df = _clean_columns(df)
        if df.empty:
            continue
        _check_rows(name, df, sheet)
        tables.append(LoadedTable(str(sheet), df))
        docs.extend(_table_documents(name, "xlsx", df, str(sheet)))
    if not docs:
        raise EmptyFileError(f"'{name}' has no data in any sheet.")
    return LoadedFile(name, "xlsx", docs, tables)


LOADERS = {".pdf": load_pdf, ".txt": load_txt, ".csv": load_csv, ".xlsx": load_xlsx}


def load_file(filename: str, data: bytes) -> LoadedFile:
    """Validate then parse a file. Raises `FileValidationError` subclasses with friendly messages."""
    ext = validate_file(filename, data)
    name = Path(filename).name
    loaded = LOADERS[ext](name, data)
    log.info("Loaded %s: %d documents, %d tables", name, len(loaded.documents), len(loaded.tables))
    return loaded
