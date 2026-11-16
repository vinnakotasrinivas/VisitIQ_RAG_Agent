import pytest

from src.ingestion.chunker import chunk_documents, chunk_text, sanitize_text
from src.ingestion.loaders import load_file
from src.utils.errors import CorruptFileError, EmptyFileError


def test_pdf_pages_have_metadata(valid_file):
    loaded = load_file(*valid_file("heritage_sites_guide.pdf"))
    assert loaded.doc_type == "pdf"
    assert [d.metadata["page"] for d in loaded.documents] == [1, 2, 3]
    assert "Golconda" in loaded.sample_text


def test_txt_loads(valid_file):
    loaded = load_file(*valid_file("visitor_faqs.txt"))
    assert "SIM" in loaded.documents[0].text


def test_csv_rows_become_documents(valid_file):
    loaded = load_file(*valid_file("attractions.csv"))
    assert len(loaded.documents) == len(loaded.tables[0].df) == 45
    first = loaded.documents[0]
    assert first.metadata["row"] == 1
    assert first.text.startswith("attractions | name: Charminar")


def test_xlsx_multiple_sheets(valid_file):
    loaded = load_file(*valid_file("transport_timetable.xlsx"))
    sheets = {t.sheet for t in loaded.tables}
    assert {"metro_lines", "metro_fares", "airport_bus", "day_passes", "local_fares"} <= sheets


def test_header_only_csv():
    with pytest.raises(EmptyFileError):
        load_file("headers.csv", b"name,area\n")


def test_malformed_csv():
    with pytest.raises(CorruptFileError):
        load_file("bad.csv", b'a,b\n1,2\n"unterminated,3,4,5\n')


def test_corrupt_pdf():
    with pytest.raises(CorruptFileError):
        load_file("broken.pdf", b"%PDF-1.4\n garbage garbage")


def test_chunking_respects_size():
    text = ("Charminar is a monument. " * 200).strip()
    chunks = chunk_text(text, size=400, overlap=60)
    assert len(chunks) > 5
    assert all(len(c) <= 460 for c in chunks)


def test_injection_lines_removed(invalid_file):
    loaded = load_file(*invalid_file("injection_doc.txt"))
    chunks, removed = chunk_documents(loaded.documents)
    joined = " ".join(c.text for c in chunks)
    assert len(removed) == 2
    assert "Ignore all previous instructions" not in joined
    assert "Nimrah Cafe" in joined


def test_sanitize_keeps_normal_text():
    clean, removed = sanitize_text("Golconda Fort opens at 09:00.\nTickets cost Rs 25.")
    assert removed == [] and "Rs 25" in clean
