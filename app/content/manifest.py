from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContentManifest:
    schemas: dict[str, str] = field(
        default_factory=lambda: {
            "places": "schemas/places.schema.json",
            "npcs": "schemas/npcs.schema.json",
            "collectibles": "schemas/collectibles.schema.json",
            "interactions": "schemas/interactions.schema.json",
            "tea": "schemas/tea.schema.json",
            "spells": "schemas/spell.schema.json",
            "storylets": "schemas/storylet.schema.json",
            "journal_page": "schemas/journal_page.schema.json",
            "lexicon": "schemas/lexicon.schema.json",
        }
    )
    assets: dict[str, str] = field(
        default_factory=lambda: {
            "places": "assets/places.json",
            "npcs": "assets/npcs.json",
            "collectibles": "assets/collectibles.json",
            "interactions": "assets/interactions.json",
            "tea": "assets/tea.json",
            "spells": "assets/spells.json",
            "storylets": "assets/storylets.json",
            "journal_templates": "journal/journal_templates.json",
        }
    )
    lexicons: dict[str, str] = field(
        default_factory=lambda: {
            "descriptive": "lexicons/descriptive_lexicon.json",
            "not_allowed": "lexicons/not_allowed_lexicon.json",
        }
    )
