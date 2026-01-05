from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from app.content.loader import load_json
from app.content.manifest import ContentManifest


def _index_by_id(items: Iterable[dict[str, Any]], id_key: str, source: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in items:
        if id_key not in item:
            raise ValueError(f"Missing {id_key} in {source}")
        item_id = str(item[id_key])
        if item_id in index:
            raise ValueError(f"Duplicate {id_key} in {source}: {item_id}")
        index[item_id] = item
    return index


class ContentRepo:
    def __init__(self, root: Path | str | None = None, manifest: ContentManifest | None = None) -> None:
        self.root = Path(root) if root else Path(__file__).resolve().parents[2]
        self.manifest = manifest or ContentManifest()

        self.places_by_id: dict[str, dict[str, Any]] = {}
        self.zones_by_id: dict[str, dict[str, Any]] = {}
        self.collectibles_by_id: dict[str, dict[str, Any]] = {}
        self.npcs_by_id: dict[str, dict[str, Any]] = {}
        self.interactions_by_id: dict[str, dict[str, Any]] = {}
        self.interactions_by_npc_kind: dict[str, list[dict[str, Any]]] = {}
        self.interactions_by_place_id: dict[str, list[dict[str, Any]]] = {}
        self.tea_by_id: dict[str, dict[str, Any]] = {}
        self.spells_by_id: dict[str, dict[str, Any]] = {}
        self.storylets_by_id: dict[str, dict[str, Any]] = {}
        self.storylets_by_place_id: dict[str, list[dict[str, Any]]] = {}
        self.journal_templates_by_entry_type: dict[str, list[dict[str, Any]]] = {}
        self.lexicon_by_key: dict[str, dict[str, Any]] = {}

        self._load_all()

    def _load_all(self) -> None:
        self._load_places()
        self._load_collectibles()
        self._load_npcs()
        self._load_interactions()
        self._load_tea()
        self._load_spells()
        self._load_storylets()
        self._load_journal_templates()
        self._load_lexicons()

    def _load_places(self) -> None:
        path = self.root / self.manifest.assets["places"]
        schema = self.root / self.manifest.schemas["places"]
        data = load_json(path, schema_path=schema) or {}
        places = data.get("places", [])
        zones = data.get("zones", [])
        self.places_by_id = _index_by_id(places, "place_id", "places")
        self.zones_by_id = _index_by_id(zones, "zone_id", "zones")

    def _load_collectibles(self) -> None:
        path = self.root / self.manifest.assets["collectibles"]
        schema = self.root / self.manifest.schemas["collectibles"]
        data = load_json(path, schema_path=schema) or {}
        collectibles = []
        for item in data.get("collectibles", []):
            item_id = item.get("item_id")
            if item_id is not None and "collectible_id" not in item:
                item = dict(item)
                item["collectible_id"] = item_id
            collectibles.append(item)
        self.collectibles_by_id = _index_by_id(collectibles, "collectible_id", "collectibles")

    def _load_npcs(self) -> None:
        path = self.root / self.manifest.assets["npcs"]
        schema = self.root / self.manifest.schemas["npcs"]
        data = load_json(path, schema_path=schema) or {}
        self.npcs_by_id = _index_by_id(data.get("npcs", []), "npc_id", "npcs")

    def _load_interactions(self) -> None:
        path = self.root / self.manifest.assets["interactions"]
        schema = self.root / self.manifest.schemas["interactions"]
        data = load_json(path, schema_path=schema) or {}
        interactions = data.get("interactions", [])
        self.interactions_by_id = _index_by_id(interactions, "interaction_id", "interactions")

        by_npc_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_place_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for interaction in interactions:
            npc_kind = interaction.get("npc_kind")
            if npc_kind:
                by_npc_kind[str(npc_kind)].append(interaction)
            conditions = interaction.get("conditions") or {}
            place_id = conditions.get("place_id")
            if place_id:
                by_place_id[str(place_id)].append(interaction)

        self.interactions_by_npc_kind = dict(by_npc_kind)
        self.interactions_by_place_id = dict(by_place_id)

    def _load_tea(self) -> None:
        path = self.root / self.manifest.assets["tea"]
        schema = self.root / self.manifest.schemas["tea"]
        data = load_json(path, schema_path=schema) or {}
        recipes = []
        for recipe in data.get("tea_recipes", []):
            recipe_id = recipe.get("recipe_id")
            if recipe_id is not None and "tea_id" not in recipe:
                recipe = dict(recipe)
                recipe["tea_id"] = recipe_id
            recipes.append(recipe)
        self.tea_by_id = _index_by_id(recipes, "tea_id", "tea_recipes")

    def _load_spells(self) -> None:
        path = self.root / self.manifest.assets["spells"]
        schema = self.root / self.manifest.schemas["spells"]
        data = load_json(path, schema_path=schema) or {}
        spells = []
        for spell in data.get("spell_recipes", []):
            spell_id = spell.get("spell_id")
            if spell_id is not None and "spell_id" not in spell:
                spell = dict(spell)
            spells.append(spell)
        self.spells_by_id = _index_by_id(spells, "spell_id", "spell_recipes")

    def _load_storylets(self) -> None:
        path = self.root / self.manifest.assets["storylets"]
        if not path.exists():
            self.storylets_by_id = {}
            self.storylets_by_place_id = {}
            return

        data = load_json(path) or {}
        storylets = data.get("storylets", []) if isinstance(data, dict) else data
        storylets = storylets or []
        self.storylets_by_id = _index_by_id(storylets, "storylet_id", "storylets")

        by_place: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for storylet in storylets:
            place_id = storylet.get("place_id")
            if place_id:
                by_place[str(place_id)].append(storylet)
        self.storylets_by_place_id = dict(by_place)

    def _load_journal_templates(self) -> None:
        path = self.root / self.manifest.assets["journal_templates"]
        data = load_json(path) or {}
        templates = data.get("templates", [])
        by_entry_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for template in templates:
            entry_type = template.get("entry_type")
            if entry_type:
                by_entry_type[str(entry_type)].append(template)
        self.journal_templates_by_entry_type = dict(by_entry_type)

    def _load_lexicons(self) -> None:
        schema = self.root / self.manifest.schemas["lexicon"]
        lexicon_entries: list[dict[str, Any]] = []
        for path in self.manifest.lexicons.values():
            data = load_json(self.root / path, schema_path=schema) or {}
            lexicon_entries.extend(data.get("lexicon", []))

        self.lexicon_by_key = _index_by_id(lexicon_entries, "key", "lexicons")
