from pathlib import Path
import sys

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root
