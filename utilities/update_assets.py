# After changing schemas in /schemas/*.schema.json, update the assets in
# /assets/*.json by running this script.

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
ASSETS_DIR = Path(__file__).parent.parent / "assets"


def _load_json(path: Path) -> Any:
	"""Return Python data parsed from the JSON file at `path`.

	:param path: File path to load.
	:type path: Path
	:return: Parsed JSON document.
	:rtype: Any
	"""
	with open(path, "r") as f:
		return json.load(f)


def _write_json(path: Path, data: Any) -> None:
	"""Serialize `data` to `path` in a pretty format and add a newline.

	:param path: Destination file to write.
	:type path: Path
	:param data: JSON-serializable document to emit.
	:type data: Any
	"""
	with open(path, "w") as f:
		json.dump(data, f, indent=2)
		f.write("\n")


def _resolve_json_pointer(document: Dict[str, Any], pointer: str) -> Any:
	"""Follow a JSON Pointer (RFC 6901) inside ``document``.

	:param document: JSON document to walk.
	:type document: Dict[str, Any]
	:param pointer: Fragment string (without '#') describing the path.
	:type pointer: str
	:return: The node pointed to by ``pointer``.
	:rtype: Any
	"""
	if not pointer:
		return document

	if pointer.startswith("/"):
		pointer = pointer[1:]

	node = document
	for token in pointer.split("/"):
		token = token.replace("~1", "/").replace("~0", "~")
		node = node[token]
	return node


def _dereference(ref: str, current_schema: Dict[str, Any], schema_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any], Path]:
	"""Resolve a JSON Schema `$ref`, loading external files when necessary.

	This uses `urllib.parse` to interpret the reference, loads the referenced
	schema file when the path points outside the current document, and follows
	the fragment through `_resolve_json_pointer` so the caller receives the
	terminal node as well as the document it originated from.

	:param ref: The raw `$ref` string that may include a file path and fragment.
	:type ref: str
	:param current_schema: Schema document that contains the `$ref`.
	:type current_schema: Dict[str, Any]
	:param schema_path: File path of `current_schema`, used to resolve relative references.
	:type schema_path: Path
	:return: Tuple containing the resolved node, the schema document that held it, and that document's path.
	:rtype: Tuple[Dict[str, Any], Dict[str, Any], Path]
	"""
	parsed = urlparse(ref)
	target_schema = current_schema
	target_path = schema_path

	if parsed.scheme or parsed.netloc or parsed.path:
		target_path = (schema_path.parent / Path(parsed.path).name).resolve()
		target_schema = _load_json(target_path)

	pointer = parsed.fragment
	node = _resolve_json_pointer(target_schema, pointer)
	return node, target_schema, target_path


def _normalize_schema(schema_node: Dict[str, Any], current_schema: Dict[str, Any], schema_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any], Path]:
	"""Unwrap oneOf/$ref helpers until a concrete node is available.

	:param schema_node: The node to normalize.
	:type schema_node: Dict[str, Any]
	:param current_schema: Schema that owns ``schema_node``.
	:type current_schema: Dict[str, Any]
	:param schema_path: File path of ``current_schema``.
	:type schema_path: Path
	:return: Tuple of the concrete node, its parent schema, and that schema’s path.
	:rtype: Tuple[Dict[str, Any], Dict[str, Any], Path]
	"""
	node = schema_node
	root_schema = current_schema
	root_path = schema_path

	while True:
		if "oneOf" in node and node["oneOf"]:
			node = node["oneOf"][0]
			continue

		if "$ref" in node:
			resolved_node, resolved_root, resolved_path = _dereference(node["$ref"], root_schema, root_path)
			node = resolved_node
			root_schema = resolved_root
			root_path = resolved_path
			continue

		break

	return node, root_schema, root_path


def _default_for_schema(schema_node: Dict[str, Any], current_schema: Dict[str, Any], schema_path: Path) -> Any:
	"""Compute a default value for the provided schema node.

	:param schema_node: Schema node to inspect for defaults.
	:type schema_node: Dict[str, Any]
	:param current_schema: Schema document containing the node.
	:type current_schema: Dict[str, Any]
	:param schema_path: File path for ``current_schema``.
	:type schema_path: Path
	:return: Default value (explicit ``default`` or a minimal placeholder).
	:rtype: Any
	"""
	node, _, _ = _normalize_schema(schema_node, current_schema, schema_path)
	if "default" in node:
		return node["default"]

	node_type = node.get("type")
	if node_type == "array":
		return []
	if node_type == "object":
		return {}
	return None


def _ensure_matches_schema(
	value: Any,
	schema_node: Dict[str, Any],
	current_schema: Dict[str, Any],
	schema_path: Path,
	path_prefix: str = "",
) -> Tuple[bool, List[str]]:
	"""Recursively add missing defaults so ``value`` conforms to ``schema_node``.

	:param value: Data to validate and potentially mutate.
	:type value: Any
	:param schema_node: Schema that describes ``value``.
	:type schema_node: Dict[str, Any]
	:param current_schema: Schema document containing ``schema_node``.
	:type current_schema: Dict[str, Any]
	:param schema_path: File path for ``current_schema``.
	:type schema_path: Path
	:param path_prefix: Dot-separated path representing ``value``’s location.
	:type path_prefix: str
	:return: Tuple of whether a mutation occurred and the list of added paths.
	:rtype: Tuple[bool, List[str]]
	"""
	node, root_schema, root_path = _normalize_schema(schema_node, current_schema, schema_path)
	typ = node.get("type")
	changed = False
	added: List[str] = []

	if typ == "object" and isinstance(value, dict):
		for prop_name, prop_schema in node.get("properties", {}).items():
			full_path = f"{path_prefix}.{prop_name}" if path_prefix else prop_name
			if prop_name not in value:
				value[prop_name] = _default_for_schema(prop_schema, root_schema, root_path)
				changed = True
				added.append(full_path)
				sub_changed, sub_added = _ensure_matches_schema(
					value[prop_name], prop_schema, root_schema, root_path, full_path
				)
				changed = changed or sub_changed
				added.extend(sub_added)
			else:
				sub_changed, sub_added = _ensure_matches_schema(
					value[prop_name], prop_schema, root_schema, root_path, full_path
				)
				changed = changed or sub_changed
				added.extend(sub_added)
		return changed, added

	if typ == "array" and isinstance(value, list):
		item_schema = node.get("items")
		if item_schema is None:
			return False, added
		for entry in value:
			entry_prefix = f"{path_prefix}[]" if path_prefix else "[]"
			sub_changed, sub_added = _ensure_matches_schema(
				entry, item_schema, root_schema, root_path, entry_prefix
			)
			changed = changed or sub_changed
			added.extend(sub_added)
		return changed, added

	return False, added


def _sync_asset(schema_path: Path) -> Tuple[Path, bool, List[str]]:
	"""Synchronize the asset JSON corresponding to ``schema_path``.

	:param schema_path: Path to the schema file to sync.
	:type schema_path: Path
	:return: Tuple of the asset file path, whether it was rewritten, and the added field paths list.
	:rtype: Tuple[Path, bool, List[str]]
	"""
	asset_name = schema_path.name
	if asset_name.endswith(".schema.json"):
		asset_name = asset_name[: -len(".schema.json")] + ".json"
	asset_path = ASSETS_DIR / asset_name
	schema = _load_json(schema_path)
	data = _load_json(asset_path) if asset_path.exists() else {}

	changed = False
	added_fields: List[str] = []
	for prop_name, prop_schema in schema.get("properties", {}).items():
		if prop_name not in data:
			data[prop_name] = _default_for_schema(prop_schema, schema, schema_path)
			changed = True
			added_fields.append(prop_name)
			sub_changed, sub_added = _ensure_matches_schema(
				data[prop_name], prop_schema, schema, schema_path, prop_name
			)
			changed = changed or sub_changed
			added_fields.extend(sub_added)
		else:
			sub_changed, sub_added = _ensure_matches_schema(
				data[prop_name], prop_schema, schema, schema_path, prop_name
			)
			changed = changed or sub_changed
			added_fields.extend(sub_added)

	if changed:
		_write_json(asset_path, data)
	return asset_path, changed, added_fields


def update_asset_file() -> Dict[str, List[str]]:
	"""Synchronize all schema-defined assets by filling in missing properties.

	This loops every ``schemas/*.schema.json`` file and ensures the
	corresponding asset has all required fields, printing status messages
	for each file processed."""
	results: Dict[str, List[str]] = {}
	for schema_file in SCHEMAS_DIR.glob("*.schema.json"):
		asset_file, changed, added_fields = _sync_asset(schema_file)
		if changed:
			seen_additions: List[str] = []
			for field in added_fields:
				if field not in seen_additions:
					seen_additions.append(field)
			results[asset_file.stem] = seen_additions
			msg = f"Asset updated: {asset_file.name}"
			if seen_additions:
				msg += " (added " + ", ".join(seen_additions) + ")"
			print(msg)
		else:
			print(f"No changes detected for {asset_file.name}.")
	return results


def update_all_assets():
	"""Update all assets based on their corresponding schemas.

	Iterates over all schema-to-file relationships and updates each asset file.
	For collection-based assets, ensures each item in the collection matches the schema.
	"""
	for schema, asset_file in SCHEMA_TO_FILE.items():
		try:
			schema_path = SCHEMAS_DIR / schema
			asset_path = ASSETS_DIR / asset_file

			if not schema_path.exists():
				print(f"Schema not found: {schema}")
				continue

			if not asset_path.exists():
				print(f"Asset file not found: {asset_file}")
				continue

			schema_data = _load_json(schema_path)
			asset_data = _load_json(asset_path)

			# Ensure each item in the collection matches the schema
			for key, entries in asset_data.items():
				if isinstance(entries, list):
					for idx, entry in enumerate(entries):
						changed, added_fields = _ensure_matches_schema(
							entry, schema_data.get("properties", {}).get(key, {}), schema_data, schema_path
						)
						if changed:
							print(f"Updated item {idx} in {asset_file}: added fields {added_fields}")

			_write_json(asset_path, asset_data)
			print(f"Updated asset: {asset_file}")

		except FileNotFoundError as e:
			print(f"Warning: {e}")

# Updated to use schema-to-file relationships for asset updates.
SCHEMA_TO_FILE = {
    "actions.schema.json": "actions.json",
    "collectibles.schema.json": "collectibles.json",
    "interactions.schema.json": "interactions.json",
    "npcs.schema.json": "npcs.json",
    "places.schema.json": "places.json",
    "players.schema.json": "player.json",
    "spells.schema.json": "spells.json",
    "teas.schema.json": "tea.json",
}

def update_assets():
    """Update assets based on their corresponding schemas."""
    for schema, asset_file in SCHEMA_TO_FILE.items():
        schema_path = SCHEMAS_DIR / schema
        asset_path = ASSETS_DIR / asset_file

        if not schema_path.exists():
            print(f"Schema not found: {schema}")
            continue

        if not asset_path.exists():
            print(f"Asset file not found: {asset_file}")
            continue

        schema_data = _load_json(schema_path)
        asset_data = _load_json(asset_path)

        # Example: Ensure all required fields exist in the asset data
        for key, value in schema_data.get("properties", {}).items():
            if key not in asset_data:
                asset_data[key] = _default_for_schema(value, schema_data, schema_path)

        _write_json(asset_path, asset_data)
        print(f"Updated asset: {asset_file}")

def update_asset_file(asset_stem: str):
    """Update a single asset file based on its corresponding schema.

    :param asset_stem: Base filename (without .json) of the target asset.
    """
    schema_file = f"{asset_stem}.schema.json"
    asset_file = f"{asset_stem}.json"

    schema_path = SCHEMAS_DIR / schema_file
    asset_path = ASSETS_DIR / asset_file

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_file}")

    if not asset_path.exists():
        raise FileNotFoundError(f"Asset file not found: {asset_file}")

    schema_data = _load_json(schema_path)
    asset_data = _load_json(asset_path)

    # Ensure all required fields exist in the asset data
    for key, value in schema_data.get("properties", {}).items():
        if key not in asset_data:
            asset_data[key] = _default_for_schema(value, schema_data, schema_path)

    _write_json(asset_path, asset_data)
    print(f"Updated asset: {asset_file}")
