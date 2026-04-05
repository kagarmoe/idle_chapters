import json
from pathlib import Path

import pytest
from jsonschema import validate

from idle_chapters.services.errors import ErrorKind


@pytest.fixture(scope="module")
def repo_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / ".git").is_dir():
            return parent
    return path.parents[3]


@pytest.fixture(scope="module")
def templates(repo_root: Path) -> dict:
    path = repo_root / "assets" / "error_templates.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema(repo_root: Path) -> dict:
    path = repo_root / "schemas" / "error_templates.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_templates_validate_against_schema(templates, schema):
    validate(instance=templates, schema=schema)


def test_every_error_kind_has_a_template(templates):
    for kind in ErrorKind:
        assert kind.value in templates, f"Missing template for {kind.value}"


def test_every_template_has_required_keys(templates):
    for kind, entry in templates.items():
        assert "template" in entry, f"{kind} missing 'template'"
        assert "fallback" in entry, f"{kind} missing 'fallback'"


# --- Tone contract compliance ---
# These words violate design-docs/game_design/tone_contract.md

DISALLOWED_WORDS = [
    "fear", "threat", "danger", "urgent", "must", "fail",
    "lose", "lost", "lack", "scarcity", "shortage", "blame",
    "fault", "risk", "deadline", "rush", "destroyed", "broken",
    "terrible", "horrible", "wrong", "error", "crash", "panic",
]


def test_player_templates_comply_with_tone_contract(templates):
    violations = []
    for kind, entry in templates.items():
        for field in ("template", "fallback"):
            text = entry.get(field, "").lower()
            for word in DISALLOWED_WORDS:
                if word in text:
                    violations.append(f"{kind}.{field} contains '{word}'")
    assert violations == [], f"Tone contract violations:\n" + "\n".join(violations)
