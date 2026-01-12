"""Helpers to backfill asset content using the ChatGPT API."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from utilities.chatgpt_query import (
	ChatGPTQuery,
	DEFAULT_MODEL,
	DEFAULT_TEMPERATURE,
)

ROOT = Path(__file__).parent.parent
ASSETS_DIR = ROOT / "assets"
TONE_CONTRACT_PATH = ROOT / "dev" / "game_design" / "tone_contract.md"
LEXICONS_DIR = ROOT / "lexicons"


def _load_json(path: Path) -> Any:
	"""Return Python data parsed from `path`."""
	with open(path, "r") as f:
		return json.load(f)


def _write_json(path: Path, data: Any) -> None:
	"""Write `data` to `path` as indented JSON."""
	with open(path, "w") as f:
		json.dump(data, f, indent=2)
		f.write("\n")


def _load_tone_contract() -> str:
	"""Read the tone contract file that bounds any generated text."""
	if not TONE_CONTRACT_PATH.exists():
		return ""
	return TONE_CONTRACT_PATH.read_text().strip()


def _load_lexicon_context() -> str:
	"""Combine every lexicon file into a single reference block."""
	parts: List[str] = []
	for lex_file in sorted(LEXICONS_DIR.glob("*.json")):
		try:
			payload = _load_json(lex_file)
		except json.JSONDecodeError:
			continue
		parts.append(f"{lex_file.name}:\n{json.dumps(payload, indent=2)}")
	return "\n\n".join(parts)


def _build_prompt(item: Dict[str, Any], missing_fields: List[str], tone_contract: str, lexicons: str) -> List[Dict[str, str]]:
	"""Build the message list that will be sent to the LLM."""
	description = json.dumps(item, indent=2)
	system_content = (
		"You are writing cozy, emotionally safe descriptions for an idle game. "
		"Obey the tone contract, use gentle imagery, and never imply urgency, scarcity, or threat."
	)
	user_content = (
		"Context:\n"
		f"{tone_contract}\n\n"
		f"Lexicons:\n{lexicons}\n\n"
		f"Item metadata:\n{description}\n\n"
		f"Fields needing text: {', '.join(missing_fields)}.\n"
		"Describe each missing field in one sentence or phrase. Return ONLY a JSON object\n"
		"mapping each missing field to its new string value."
	)
	return [
		{"role": "system", "content": system_content},
		{"role": "user", "content": user_content},
	]


def _missing_string_fields(entry: Dict[str, Any]) -> List[str]:
	"""Return string keys that are either missing or blank."""
	result = []
	for key, value in entry.items():
		if isinstance(value, str) and not value.strip():
			result.append(key)
	return result


def backfill_assets(
	asset_stem: str,
	*,
	model: str = DEFAULT_MODEL,
	temperature: float = DEFAULT_TEMPERATURE,
	client: Optional[ChatGPTQuery] = None,
) -> List[str]:
	"""Backfill blank string fields in `assets/<asset_stem>.json` via ChatGPT.

	:param asset_stem: Base filename (without .json) of the target asset.
	:param model: OpenAI chat model to use.
	:param temperature: Temperature for the completion.
	:param client: Optional ChatGPTQuery instance (for caching/testing).
	:return: List of dotted paths that were updated.
	"""
	asset_path = ASSETS_DIR / f"{asset_stem}.json"
	if not asset_path.exists():
		raise FileNotFoundError(f"{asset_path} does not exist.")

	data = _load_json(asset_path)
	tone_contract = _load_tone_contract()
	lexicons = _load_lexicon_context()
	updates: List[str] = []
	collection_keys = [key for key, value in data.items() if isinstance(value, list)]
	client = client or ChatGPTQuery(model=model, temperature=temperature)

	for key in collection_keys:
		entries = data[key]
		for idx, entry in enumerate(entries):
			if not isinstance(entry, dict):
				continue
			missing = _missing_string_fields(entry)
			if not missing:
				continue
			messages = _build_prompt(entry, missing, tone_contract, lexicons)
			cache_key = f"{asset_stem}.{key}[{idx}].{','.join(missing)}"
			response, _ = client.ask(messages, cache_key=cache_key)
			response = response.strip()
			try:
				completion = json.loads(response)
			except json.JSONDecodeError as exc:
				raise ValueError("ChatGPT response was not valid JSON.") from exc
			for field, value in completion.items():
				if field not in missing:
					continue
				entry[field] = value
				updates.append(f"{asset_stem}.{key}[{idx}].{field}")

	if updates:
		_write_json(asset_path, data)
	return updates


def backfill_all_assets(
	*,
	model: str = DEFAULT_MODEL,
	temperature: float = DEFAULT_TEMPERATURE,
	client: Optional[ChatGPTQuery] = None,
	exclude: Optional[List[str]] = None,
	updated_assets: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, List[str]]:
	"""Backfill every JSON asset in `assets/`, optionally skipping some.

	:param model: OpenAI chat model to use.
	:param temperature: Sampling temperature.
	:param client: Optional shared `ChatGPTQuery` instance.
	:param exclude: Asset stems (without `.json`) to skip.
	:return: Mapping from asset stem to the dotted paths that were updated.
	"""
	client = client or ChatGPTQuery(model=model, temperature=temperature)
	exclude_set = set(exclude or [])
	results: Dict[str, List[str]] = {}
	targets = (
		{Path(key).stem for key in updated_assets.keys()}
		if updated_assets is not None
		else {asset_file.stem for asset_file in ASSETS_DIR.glob("*.json")}
	)
	for asset_file in sorted(ASSETS_DIR.glob("*.json")):
		asset_stem = asset_file.stem
		if asset_stem in exclude_set or (updated_assets is not None and asset_stem not in targets):
			continue
		updates = backfill_assets(asset_stem, model=model, temperature=temperature, client=client)
		if updates:
			results[asset_stem] = updates
	return results
