import json
from pathlib import Path

from app.content.schema_utils import load_validator


def test_player_schema_accepts_counts(repo_root: Path) -> None:
    schema_path = repo_root / "schemas" / "player.schema.json"
    validator = load_validator(schema_path)

    player = {
        "address": {"display_name": "Rowan", "pronouns": "they_them"},
        "state": {
            "current_location": "cottage_home",
            "inventory": ["journal"],
            "inventory_counts": {"journal": 1},
            "visit_counts": {"cottage_home": 2},
            "seen_interactions": {"human_ambient_weather_01": 1},
            "flags": ["all_portals_opened"],
        },
    }

    validator.validate(instance=player)
