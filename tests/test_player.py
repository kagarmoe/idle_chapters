from app.content.schema_utils import load_validator
from texts.welcome import _create_player


def test_create_player_sets_player_id(monkeypatch, repo_root) -> None:
    schema_path = repo_root / "schemas" / "player.schema.json"
    validator = load_validator(schema_path)

    inputs = iter(["Rowan", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    player = _create_player()
    assert player is not None
    assert player.get("player_id")
    validator.validate(instance=player)
