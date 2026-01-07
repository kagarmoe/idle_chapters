from __future__ import annotations

import json
from pathlib import Path

import jsonschema


def load_validator(schema_path: Path) -> jsonschema.Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    store = {}
    for candidate in schema_path.parent.glob("*.json"):
        try:
            candidate_schema = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        schema_id = candidate_schema.get("$id")
        if schema_id:
            store[schema_id] = candidate_schema
    resolver = jsonschema.RefResolver(
        base_uri=schema_path.resolve().as_uri(),
        referrer=schema,
        store=store,
    )
    return jsonschema.Draft202012Validator(schema, resolver=resolver)
