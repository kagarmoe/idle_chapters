import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / ".git").is_dir():
            return parent
    return path.parents[1]


@pytest.fixture(scope="session")
def api_root(repo_root: Path) -> Path:
    return repo_root


@pytest.fixture(autouse=True, scope="session")
def disable_otel() -> None:
    os.environ.setdefault("OTEL_DISABLED", "true")
