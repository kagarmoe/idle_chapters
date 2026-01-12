"""Reusable ChatGPT client with caching and defaults for cost control."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

API_URL = "https://api.openai.com/v1/chat/completions"
CACHE_FILE = Path(__file__).parent / ".chatgpt_cache.json"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.3


class ChatGPTQuery:
	"""Lightweight ChatGPT helper that reuses cached responses."""

	def __init__(
		self,
		model: str = DEFAULT_MODEL,
		temperature: float = DEFAULT_TEMPERATURE,
		cache_path: Optional[Path] = None,
	):
		self.model = model
		self.temperature = temperature
		self.cache_path = cache_path or CACHE_FILE
		self.cache_path.parent.mkdir(parents=True, exist_ok=True)
		self._cache = self._load_cache()

	def _load_cache(self) -> Dict[str, str]:
		if self.cache_path.exists():
			try:
				return json.loads(self.cache_path.read_text())
			except json.JSONDecodeError:
				return {}
		return {}

	def _save_cache(self) -> None:
		self.cache_path.write_text(json.dumps(self._cache, indent=2))

	def _hash_messages(self, messages: List[Dict[str, str]]) -> str:
		payload = json.dumps(messages, ensure_ascii=False, sort_keys=True)
		return hashlib.sha256(payload.encode("utf-8")).hexdigest()

	def ask(
		self,
		messages: List[Dict[str, str]],
		*,
		cache_key: Optional[str] = None,
		use_cache: bool = True,
	) -> Tuple[str, Optional[Dict[str, Any]]]:
		"""Ask the model and return the content (plus usage info)."""
		key = cache_key or self._hash_messages(messages)
		if use_cache and key in self._cache:
			return self._cache[key], None

		api_key = os.environ.get("OPENAI_API_KEY")
		if not api_key:
			raise EnvironmentError("OPENAI_API_KEY must be set for ChatGPT queries.")

		headers = {
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json",
		}
		payload = {
			"model": self.model,
			"temperature": self.temperature,
			"messages": messages,
		}

		response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
		response.raise_for_status()
		body = response.json()
		choices = body.get("choices", [])
		if not choices:
			raise ValueError("ChatGPT returned no choices.")

		content = choices[0]["message"]["content"]
		usage = body.get("usage")

		self._cache[key] = content
		self._save_cache()
		return content, usage
