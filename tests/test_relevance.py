import pytest

from src.config import VALID_SAMPLE_DIR
from src.ingestion.loaders import load_file
from src.ingestion.relevance import check_relevance


@pytest.mark.parametrize("name", sorted(p.name for p in VALID_SAMPLE_DIR.iterdir()))
def test_all_valid_samples_are_relevant(valid_file, name):
    loaded = load_file(*valid_file(name))
    res = check_relevance(loaded.sample_text, loaded.name)
    assert res.relevant, f"{name}: {res.reason}"


def test_pharmacy_invoice_rejected(invalid_file):
    loaded = load_file(*invalid_file("pharmacy_invoice.pdf"))
    res = check_relevance(loaded.sample_text, loaded.name)
    assert not res.relevant
    assert "pharmacy" in res.reason


def test_other_city_guide_rejected(invalid_file):
    loaded = load_file(*invalid_file("bengaluru_guide.pdf"))
    res = check_relevance(loaded.sample_text, loaded.name)
    assert not res.relevant
    assert "not Hyderabad" in res.reason


def test_generic_text_rejected():
    res = check_relevance("Quarterly meeting notes. Action items: update the roadmap and hire two engineers.", "notes.txt")
    assert not res.relevant


def test_hyderabad_without_tourism_rejected():
    res = check_relevance("Hyderabad", "x.txt")
    assert not res.relevant


def test_short_hyderabad_tip_accepted():
    res = check_relevance("Visit Charminar early in the morning, then eat biryani near Laad Bazaar. Tickets are cheap.",
                          "tips.txt")
    assert res.relevant
