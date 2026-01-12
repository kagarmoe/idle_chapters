import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Ensure utilities package is on sys.path when running tests directly
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utilities import backfill_assets as backfill_module


def _prepare_env(tmp_path: Path) -> Path:
    tone_path = tmp_path / "dev" / "game_design"
    tone_path.mkdir(parents=True, exist_ok=True)
    (tone_path / "tone_contract.md").write_text("gentle tone")

    lex_dir = tmp_path / "lexicons"
    lex_dir.mkdir()
    (lex_dir / "descriptive_lexicon.json").write_text(json.dumps({"hello": ["warm"]}))
    backfill_module.LEXICONS_DIR = lex_dir
    return tone_path / "tone_contract.md"


class DummyClient:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def ask(self, messages, cache_key=None, use_cache=True):
        self.calls.append((messages, cache_key, use_cache))
        return json.dumps({"notes": "soft warmth"}), {}


class FailingClient(DummyClient):
    def ask(self, *args, **kwargs):
        raise ValueError("should not be called")


class InvalidClient(DummyClient):
    def ask(self, *args, **kwargs):
        return "not json", {}


def test_backfill_assets_updates_blank_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    asset_path = assets_dir / "demo.json"
    asset_path.write_text(json.dumps({"items": [{"item_id": "sample", "display_name": "Sample", "notes": ""}]}))

    tone_path = _prepare_env(tmp_path)

    monkeypatch.setattr(backfill_module, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(backfill_module, "TONE_CONTRACT_PATH", tone_path)

    client = DummyClient()
    monkeypatch.setattr(backfill_module, "ChatGPTQuery", lambda *args, **kwargs: client)

    updated = backfill_module.backfill_assets("demo")

    assert "demo.items[0].notes" in updated
    data = json.loads(asset_path.read_text())
    assert data["items"][0]["notes"] == "soft warmth"
    assert client.calls


def test_backfill_assets_skips_when_no_blank(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    asset_path = assets_dir / "demo.json"
    asset_path.write_text(json.dumps({"items": [{"notes": "already"}]}))

    tone_path = _prepare_env(tmp_path)

    monkeypatch.setattr(backfill_module, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(backfill_module, "TONE_CONTRACT_PATH", tone_path)

    monkeypatch.setattr(backfill_module, "ChatGPTQuery", lambda *args, **kwargs: FailingClient())

    updated = backfill_module.backfill_assets("demo")
    assert updated == []


def test_backfill_assets_invalid_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    asset_path = assets_dir / "demo.json"
    asset_path.write_text(json.dumps({"items": [{"notes": ""}]}))

    tone_path = _prepare_env(tmp_path)

    monkeypatch.setattr(backfill_module, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(backfill_module, "TONE_CONTRACT_PATH", tone_path)

    monkeypatch.setattr(backfill_module, "ChatGPTQuery", lambda *args, **kwargs: InvalidClient())

    with pytest.raises(ValueError):
        backfill_module.backfill_assets("demo")


def test_backfill_all_assets_runs_every_asset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "alpha.json").write_text(json.dumps({"items": [{"notes": ""}]}))
    (assets_dir / "beta.json").write_text(json.dumps({"items": [{"notes": ""}]}))

    tone_path = _prepare_env(tmp_path)

    monkeypatch.setattr(backfill_module, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(backfill_module, "TONE_CONTRACT_PATH", tone_path)

    client = DummyClient()
    monkeypatch.setattr(backfill_module, "ChatGPTQuery", lambda *args, **kwargs: client)

    results = backfill_module.backfill_all_assets()

    assert "alpha" in results
    assert "beta" in results
    assert client.calls


def test_backfill_all_assets_respects_exclude(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "alpha.json").write_text(json.dumps({"items": [{"notes": ""}]}))

    tone_path = _prepare_env(tmp_path)

    monkeypatch.setattr(backfill_module, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(backfill_module, "TONE_CONTRACT_PATH", tone_path)

    client = DummyClient()
    monkeypatch.setattr(backfill_module, "ChatGPTQuery", lambda *args, **kwargs: client)

    results = backfill_module.backfill_all_assets(exclude=["alpha"])

    assert results == {}


def test_backfill_all_assets_uses_updated_assets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "alpha.json").write_text(json.dumps({"items": [{"notes": ""}]}))
    (assets_dir / "beta.json").write_text(json.dumps({"items": [{"notes": ""}]}))

    tone_path = _prepare_env(tmp_path)

    monkeypatch.setattr(backfill_module, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(backfill_module, "TONE_CONTRACT_PATH", tone_path)

    client = DummyClient()
    monkeypatch.setattr(backfill_module, "ChatGPTQuery", lambda *args, **kwargs: client)

    results = backfill_module.backfill_all_assets(updated_assets={"alpha.json": ["items"]})

    assert "alpha" in results
    assert "beta" not in results
