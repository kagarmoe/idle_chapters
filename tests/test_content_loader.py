from pathlib import Path

import pytest


def test_load_json_parses(repo_root: Path) -> None:
    from app.content.loader import load_json

    data = load_json(repo_root / "assets" / "places.json")
    assert isinstance(data, (dict, list))


def test_load_json_validates_schema(repo_root: Path) -> None:
    from app.content.loader import load_json

    invalid_path = repo_root / "tests" / "fixtures" / "invalid_places.json"
    schema_path = repo_root / "schemas" / "places.schema.json"

    with pytest.raises(ValueError):
        load_json(invalid_path, schema_path=schema_path)
