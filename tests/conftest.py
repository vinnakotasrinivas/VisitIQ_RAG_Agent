import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import INVALID_SAMPLE_DIR, VALID_SAMPLE_DIR  # noqa: E402


def _ensure_samples() -> None:
    if not (VALID_SAMPLE_DIR / "attractions.csv").exists() or not (INVALID_SAMPLE_DIR / "sample.jpg").exists():
        from scripts.generate_sample_docs import write_invalid, write_valid
        write_valid(VALID_SAMPLE_DIR)
        write_invalid(INVALID_SAMPLE_DIR, oversize=False)


_ensure_samples()


@pytest.fixture
def valid_file():
    def _read(name: str) -> tuple[str, bytes]:
        return name, (VALID_SAMPLE_DIR / name).read_bytes()
    return _read


@pytest.fixture
def invalid_file():
    def _read(name: str) -> tuple[str, bytes]:
        return name, (INVALID_SAMPLE_DIR / name).read_bytes()
    return _read
