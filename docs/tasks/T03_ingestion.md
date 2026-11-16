# T03 - Ingestion: validators, loaders, chunker

**Goal**: turn an uploaded file into clean, metadata-rich chunks, or a clear error.

## Files
- `src/ingestion/validators.py`: `validate_file(name, data: bytes) -> str (extension)`
- `src/ingestion/loaders.py`: `load_file(name, data) -> LoadedFile(documents, tables)`
- `src/ingestion/chunker.py`: `chunk_documents(docs)`, `sanitize_text(text) -> (clean, removed_lines)`
- `tests/test_validators.py`, `tests/test_loaders.py`

## Rules
| Check | Error class | Message |
|-------|-------------|---------|
| Extension not in {pdf, txt, csv, xlsx} | `UnsupportedFileTypeError` | "'.jpg' files are not supported. Please upload PDF, TXT, CSV or XLSX." |
| Size > 19 MB | `FileTooLargeError` | "File is 20.0 MB; the limit is 19 MB." |
| 0 bytes / no text | `EmptyFileError` | "The file is empty." |
| Magic bytes mismatch | `CorruptFileError` | "This file does not look like a real PDF." |
| Parser exception | `CorruptFileError` | "Could not read the file; it may be damaged or password protected." |

Chunking: PDFs and TXTs are split on paragraphs into chunks of about 800 characters with 120 overlap. Each table row becomes
`"<table> | col: value | ..."`. Lines that match prompt-injection patterns are removed and reported.

## Verify
```powershell
pytest tests/test_validators.py tests/test_loaders.py -v
```

## Done when
- [ ] All four formats load; JPG / ZIP / fake PDF / empty CSV raise the right error.
