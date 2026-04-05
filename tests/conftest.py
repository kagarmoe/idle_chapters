import os
from pathlib import Path
import sys

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / "CLAUDE.md").exists():
            root = parent
            break
    else:
        root = path.parents[3]
    api_dir = root / "apps" / "api"
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    return root


@pytest.fixture(scope="session")
def api_root(repo_root: Path) -> Path:
    return repo_root / "apps" / "api"


@pytest.fixture(autouse=True, scope="session")
def disable_otel() -> None:
    os.environ.setdefault("OTEL_DISABLED", "true")
