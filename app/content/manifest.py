from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContentManifest:
    schemas: dict[str, str] = field(
        default_factory=lambda: {
            "common": "schemas/common.schema.json",
            "conditions": "schemas/conditions.schema.json",
            "places": "schemas/places.schema.json",
            "npcs": "schemas/npcs.schema.json",
            "collectibles": "schemas/collectibles.schema.json",
            "interactions": "schemas/interactions.schema.json",
            "actions": "schemas/actions.schema.json",
            "scene": "schemas/scene.schema.json",
            "scene_manifest": "schemas/scenes_manifest.schema.json",
            "tea": "schemas/teas.schema.json",
            "spells": "schemas/spells.schema.json",
            "journal_page": "schemas/journal_page.schema.json",
            "journal_templates": "schemas/journal_templates.schema.json",
            "session": "schemas/sessions.schema.json",
            "lexicon": "schemas/lexicons.schema.json",
            "ingredient_substitutions": "schemas/ingredient_substitutions.schema.json",
        }
    )
    assets: dict[str, str] = field(
        default_factory=lambda: {
            "places": "assets/places.json",
            "npcs": "assets/npcs.json",
            "collectibles": "assets/collectibles.json",
            "interactions": "assets/interactions.json",
            "actions": "assets/actions.json",
            "scene_manifest": "assets/scenes/manifest.json",
            "tea": "assets/tea.json",
            "spells": "assets/spells.json",
            "journal_templates": "assets/journal_templates.json",
            "ingredient_substitutions": "assets/ingredient_substitutions.json",
        }
    )
    lexicons: dict[str, str] = field(
        default_factory=lambda: {
            "descriptive": "lexicons/descriptive_lexicon.json",
            "not_allowed": "lexicons/not_allowed_lexicon.json",
        }
    )
