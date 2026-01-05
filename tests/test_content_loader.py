from pathlib import Path

import pytest


def test_load_yaml_parses(repo_root: Path) -> None:
    from app.content.loader import load_yaml

    data = load_yaml(repo_root / "assets" / "places.yaml")
    assert isinstance(data, (dict, list))


def test_load_yaml_validates_schema(repo_root: Path) -> None:
    from app.content.loader import load_yaml

    invalid_path = repo_root / "tests" / "fixtures" / "invalid_places.yaml"
    schema_path = repo_root / "schemas" / "places.schema.yaml"

    with pytest.raises(ValueError):
        load_yaml(invalid_path, schema_path=schema_path)
