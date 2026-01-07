import os
from pathlib import Path
import sys

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


@pytest.fixture(autouse=True, scope="session")
def disable_otel() -> None:
    os.environ.setdefault("OTEL_DISABLED", "true")
