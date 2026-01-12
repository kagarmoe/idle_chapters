import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utilities import update_assets


def _write_schema(path: Path, schema: dict) -> None:
    path.write_text(json.dumps(schema))


def _write_asset(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data))


def test_update_asset_file_adds_missing_item_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    schema_dir = tmp_path / "schemas"
    assets_dir = tmp_path / "assets"
    schema_dir.mkdir()
    assets_dir.mkdir()

    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "identifier": {"type": "string"},
                        "notes": {"type": "string", "default": "gentle"}
                    }
                },
                "default": []
            }
        }
    }

    schema_path = schema_dir / "demo.schema.json"
    _write_schema(schema_path, schema)

    asset_path = assets_dir / "demo.json"
    _write_asset(asset_path, {"items": [{"identifier": "first"}]})

    monkeypatch.setattr(update_assets, "SCHEMAS_DIR", schema_dir)
    monkeypatch.setattr(update_assets, "ASSETS_DIR", assets_dir)

    result = update_assets.update_asset_file()

    data = json.loads(asset_path.read_text())
    assert data["items"][0]["identifier"] == "first"
    assert data["items"][0]["notes"] == "gentle"
    assert result["demo"] == ["items[].notes"]


def test_update_asset_file_inserts_missing_root_property(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    schema_dir = tmp_path / "schemas"
    assets_dir = tmp_path / "assets"
    schema_dir.mkdir()
    assets_dir.mkdir()

    schema = {
        "type": "object",
        "properties": {
            "things": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"label": {"type": "string"}}
                },
                "default": []
            }
        }
    }

    schema_path = schema_dir / "demo.schema.json"
    _write_schema(schema_path, schema)

    asset_path = assets_dir / "demo.json"
    _write_asset(asset_path, {})

    monkeypatch.setattr(update_assets, "SCHEMAS_DIR", schema_dir)
    monkeypatch.setattr(update_assets, "ASSETS_DIR", assets_dir)

    result = update_assets.update_asset_file()

    data = json.loads(asset_path.read_text())
    assert data["things"] == []
    assert result["demo"] == ["things"]


def test_update_all_assets_delegates_to_update_asset_file(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"count": 0}

    def fake_update():
        called["count"] += 1

    monkeypatch.setattr(update_assets, "update_asset_file", fake_update)

    update_assets.update_all_assets()
    assert called["count"] == 1
