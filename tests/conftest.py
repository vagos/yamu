from __future__ import annotations

from pathlib import Path
import pytest

from yamu.library.library import Library


@pytest.fixture()
def library(tmp_path: Path) -> Library:
    db_path = tmp_path / "library.db"
    lib = Library(str(db_path))
    try:
        yield lib
    finally:
        lib.close()
