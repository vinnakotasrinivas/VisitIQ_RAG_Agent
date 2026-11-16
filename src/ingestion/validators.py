"""File-level validation: extension allowlist, size limit, empty files and magic-byte checks."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from src.config import ALLOWED_EXTENSIONS, MAX_FILE_BYTES, MAX_FILE_MB
from src.utils.errors import CorruptFileError, EmptyFileError, FileTooLargeError, UnsupportedFileTypeError

SIGNATURES = [
    (b"\xff\xd8\xff", "a JPEG image"),
    (b"\x89PNG\r\n\x1a\n", "a PNG image"),
    (b"GIF8", "a GIF image"),
    (b"%PDF-", "a PDF document"),
    (b"PK\x03\x04", "a ZIP-based file"),
    (b"\xd0\xcf\x11\xe0", "a legacy Microsoft Office file"),
    (b"Rar!", "a RAR archive"),
    (b"7z\xbc\xaf", "a 7-Zip archive"),
    (b"MZ", "a Windows executable"),
]

FRIENDLY_TYPES = {
    ".jpg": "JPEG images", ".jpeg": "JPEG images", ".png": "PNG images", ".gif": "GIF images", ".zip": "ZIP archives",
    ".rar": "RAR archives", ".7z": "7-Zip archives", ".docx": "Word documents", ".doc": "Word documents",
    ".pptx": "PowerPoint files", ".exe": "programs", ".json": "JSON files", ".html": "web pages", ".mp4": "videos",
}


def sniff(data: bytes) -> str | None:
    """Describe the real content type from magic bytes, or None for plain text / unknown."""
    head = data[:16]
    for sig, label in SIGNATURES:
        if head.startswith(sig):
            return label
    return None


def _looks_binary(data: bytes) -> bool:
    sample = data[:8192]
    return b"\x00" in sample


def validate_file(filename: str, data: bytes) -> str:
    """Validate an uploaded file and return its normalised extension (e.g. '.pdf').

    Raises a `FileValidationError` subclass with a user-friendly message on failure.
    """
    name = Path(filename or "").name
    ext = Path(name).suffix.lower()
    allowed = ", ".join(sorted(e.lstrip(".").upper() for e in ALLOWED_EXTENSIONS))

    if not ext:
        raise UnsupportedFileTypeError(f"'{name or 'file'}' has no extension. Please upload {allowed} files.")
    if ext == ".xls":
        raise UnsupportedFileTypeError("Old Excel '.xls' files are not supported. Please re-save the file as '.xlsx'.")
    if ext not in ALLOWED_EXTENSIONS:
        kind = FRIENDLY_TYPES.get(ext, f"'{ext}' files")
        raise UnsupportedFileTypeError(f"{kind[0].upper() + kind[1:]} are not supported ('{name}'). "
                                       f"Please upload {allowed} files.")

    size = len(data)
    if size == 0:
        raise EmptyFileError(f"'{name}' is empty (0 bytes).")
    if size > MAX_FILE_BYTES:
        raise FileTooLargeError(f"'{name}' is {size / (1024 * 1024):.1f} MB; the limit is {MAX_FILE_MB} MB per file.")

    real = sniff(data)
    if ext == ".pdf":
        if b"%PDF-" not in data[:1024]:
            what = f" It looks like {real}." if real else ""
            raise CorruptFileError(f"'{name}' is not a valid PDF.{what}")
    elif ext == ".xlsx":
        if real != "a ZIP-based file":
            what = f" It looks like {real}." if real else ""
            raise CorruptFileError(f"'{name}' is not a valid Excel (.xlsx) workbook.{what}")
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = set(zf.namelist())
        except zipfile.BadZipFile as exc:
            raise CorruptFileError(f"'{name}' is damaged and cannot be opened as an Excel workbook.") from exc
        if "xl/workbook.xml" not in names:
            raise CorruptFileError(f"'{name}' is a ZIP archive, not an Excel workbook.")
    else:  # .txt / .csv
        if real is not None:
            raise CorruptFileError(f"'{name}' should be plain text but looks like {real}.")
        if _looks_binary(data):
            raise CorruptFileError(f"'{name}' contains binary data and is not a readable text file.")
        if not data.strip():
            raise EmptyFileError(f"'{name}' contains only whitespace.")
    return ext
