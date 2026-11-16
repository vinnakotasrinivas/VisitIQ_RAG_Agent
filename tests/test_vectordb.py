import pytest

from src.data.tables import TableRegistry
from src.ingestion.pipeline import ingest_file
from src.vectordb.store import VectorStore


@pytest.fixture(scope="module")
def kb(tmp_path_factory):
    base = tmp_path_factory.mktemp("kb")
    store = VectorStore(path=base / "chroma", collection="test_collection")
    registry = TableRegistry(base / "tables")
    from src.config import VALID_SAMPLE_DIR
    for name in ["safety_etiquette_advisory.pdf", "heritage_sites_guide.pdf", "visitor_faqs.txt", "attractions.csv"]:
        rep = ingest_file(name, (VALID_SAMPLE_DIR / name).read_bytes(), store, registry)
        assert rep.accepted, rep.error
    return store, registry


def test_stats_counts_sources(kb):
    store, _ = kb
    stats = store.stats()
    assert stats["chunks"] > 50
    assert set(stats["sources"]) == {"safety_etiquette_advisory.pdf", "heritage_sites_guide.pdf", "visitor_faqs.txt",
                                     "attractions.csv"}


def test_semantic_search_finds_dress_code(kb):
    store, _ = kb
    hits = store.search("what should I wear when visiting a mosque", k=3)
    assert hits and hits[0]["metadata"]["source"] == "safety_etiquette_advisory.pdf"
    assert 0 < hits[0]["similarity"] <= 1


def test_search_returns_page_metadata(kb):
    store, _ = kb
    hits = store.search("Golconda Fort acoustics handclap", k=2)
    assert hits[0]["metadata"]["source"] == "heritage_sites_guide.pdf"
    assert hits[0]["metadata"]["page"] == 2


def test_reingest_is_idempotent(kb):
    store, registry = kb
    from src.config import VALID_SAMPLE_DIR
    before = store.count()
    ingest_file("visitor_faqs.txt", (VALID_SAMPLE_DIR / "visitor_faqs.txt").read_bytes(), store, registry)
    assert store.count() == before


def test_irrelevant_query_filtered_by_threshold(kb):
    store, _ = kb
    hits = store.search("quantum chromodynamics lattice gauge theory", k=5, min_similarity=0.45)
    assert hits == []


def test_tables_registered(kb):
    _, registry = kb
    df = registry.get("attractions")
    assert df is not None and "Charminar" in set(df["name"])
