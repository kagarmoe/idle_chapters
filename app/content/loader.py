from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import SchemaError, ValidationError

from app.content.schema_utils import load_validator

def load_json(path: Path | str, schema_path: Path | str | None = None) -> Any:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON: {path}") from exc

    if schema_path is not None:
        schema_path = Path(schema_path)
        try:
            validator = load_validator(schema_path)
            validator.validate(instance=data)
        except (ValidationError, SchemaError) as exc:
            raise ValueError(f"Schema validation failed for {path}: {exc.message}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to load schema: {schema_path}") from exc

    return data
