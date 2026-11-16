import pytest

from src.config import MAX_FILE_BYTES
from src.ingestion.validators import validate_file
from src.utils.errors import CorruptFileError, EmptyFileError, FileTooLargeError, UnsupportedFileTypeError


@pytest.mark.parametrize("name", ["hyderabad_visitor_guide.pdf", "visitor_faqs.txt", "attractions.csv",
                                  "events_calendar.xlsx", "transport_timetable.xlsx"])
def test_valid_files_pass(valid_file, name):
    fname, data = valid_file(name)
    assert validate_file(fname, data) in {".pdf", ".txt", ".csv", ".xlsx"}


@pytest.mark.parametrize("name", ["sample.jpg", "archive.zip"])
def test_unsupported_types(invalid_file, name):
    fname, data = invalid_file(name)
    with pytest.raises(UnsupportedFileTypeError) as exc:
        validate_file(fname, data)
    assert "not supported" in exc.value.user_message


def test_xls_gets_specific_message():
    with pytest.raises(UnsupportedFileTypeError, match="xlsx"):
        validate_file("old.xls", b"\xd0\xcf\x11\xe0" + b"0" * 100)


def test_no_extension():
    with pytest.raises(UnsupportedFileTypeError):
        validate_file("README", b"hello")


def test_fake_pdf_detected(invalid_file):
    fname, data = invalid_file("fake_pdf.pdf")
    with pytest.raises(CorruptFileError) as exc:
        validate_file(fname, data)
    assert "JPEG" in exc.value.user_message


def test_empty_file(invalid_file):
    fname, data = invalid_file("empty.csv")
    with pytest.raises(EmptyFileError):
        validate_file(fname, data)


def test_whitespace_only_txt():
    with pytest.raises(EmptyFileError):
        validate_file("blank.txt", b"   \n\n  ")


def test_too_large():
    with pytest.raises(FileTooLargeError) as exc:
        validate_file("big.txt", b"a" * (MAX_FILE_BYTES + 1))
    assert "19 MB" in exc.value.user_message


def test_exactly_at_limit_is_ok():
    assert validate_file("edge.txt", b"a" * MAX_FILE_BYTES) == ".txt"


def test_zip_renamed_to_xlsx(invalid_file):
    _, data = invalid_file("archive.zip")
    with pytest.raises(CorruptFileError, match="not an Excel"):
        validate_file("renamed.xlsx", data)


def test_binary_in_txt():
    with pytest.raises(CorruptFileError):
        validate_file("bin.txt", b"abc\x00\x01\x02def")


def test_image_renamed_to_csv(invalid_file):
    _, data = invalid_file("sample.jpg")
    with pytest.raises(CorruptFileError, match="JPEG"):
        validate_file("photo.csv", data)
