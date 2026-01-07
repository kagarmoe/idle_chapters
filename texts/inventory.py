import json
from pathlib import Path

from jsonschema import SchemaError, ValidationError

from app.content.loader import load_json
from app.content.schema_utils import load_validator
REPO_ROOT = Path(__file__).resolve().parents[1]
COLLECTIBLES_FILE = REPO_ROOT / "assets" / "collectibles.json"
INVENTORY_DIR = REPO_ROOT / "assets" / "inventories"
INVENTORY_SCHEMA = REPO_ROOT / "schemas" / "collectibles.schema.json"


def inventory_path(player_id):
    return INVENTORY_DIR / f"{player_id}.json"


def _load_collectibles_index():
    data = load_json(COLLECTIBLES_FILE)
    items = data.get("collectibles", [])
    return {item["item_id"]: item for item in items if "item_id" in item}


def _validate_inventory(payload):
    try:
        validator = load_validator(INVENTORY_SCHEMA)
        validator.validate(instance=payload)
    except (ValidationError, SchemaError) as exc:
        print(f"Inventory failed schema validation: {exc.message}")
        return False
    return True


def load_inventory(player_id):
    path = inventory_path(player_id)
    if not path.exists():
        return set()
    try:
        data = load_json(path, schema_path=INVENTORY_SCHEMA)
    except (ValueError, FileNotFoundError):
        print("Inventory file is invalid; starting with an empty inventory.")
        return set()
    return {item.get("item_id") for item in data.get("collectibles", []) if item.get("item_id")}


def save_inventory(player_id, inventory_ids):
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
    collectibles = _load_collectibles_index()
    inventory_items = []
    for item_id in sorted(inventory_ids):
        item = collectibles.get(item_id)
        if item:
            inventory_items.append(item)
        else:
            print(f"Note: inventory item '{item_id}' not found in collectibles.")
    if not inventory_items:
        print("Inventory is empty; skipping inventory save.")
        return
    payload = {"collectibles": inventory_items}
    if not _validate_inventory(payload):
        return
    inventory_path(player_id).write_text(json.dumps(payload, indent=4), encoding="utf-8")
