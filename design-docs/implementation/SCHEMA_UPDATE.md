# Schema update plan (actions + intent parsing)

## Purpose

Define schema changes needed to support freeform CLI intent parsing while preserving the schema-first design contract and engine eligibility rules.

## Scope

This update introduces:

- Action objects with intent signatures
- Scene graphs (per-file) with a manifest
- Result variants for repeated outcomes
- Location-level visible NPCs (always-present only)
- A clear separation of **provenance** vs **availability**

## Proposed Schema Changes

### 1) Action Schema (new or extension of interaction)

Add an `action` object that is content-shaped and validated.

**Fields**

- `action_id` (string, required)
- `label` (string, required)
- `when` (conditions object, optional)
- `effects` (array, optional)
- `result` (string, optional)
- `result_variants` (array of strings, optional)
- `intent_signature` (object, required for CLI)
  - `keywords` (array of strings)
  - `phrases` (array of strings)

**Notes**

- `result_variants` is used when the action is repeatable.
- `result` is allowed for a single, stable outcome.
- `when` continues to control eligibility.

### 2) Provenance vs Availability (data design)

**Provenance** answers: “Where does an item generally come from?”
This belongs in `collectibles.schema.json` via `origin_scope` and `origin_ref`. It is global, static metadata used by generators and world logic.

**Availability** answers: “What is visible/takeable here right now?”
This should be driven by **actions/scenes** (eligibility rules), and is the canonical source for UI prompts like “What is here?”

**Recommendation**

- Keep provenance in `collectibles` only.
- Drive availability through action eligibility and effects.
- Avoid duplicating origin data inside places.

### 3) Location Schema (extension)

Add per-location declarations for:

- `visible_npcs` (always-present only)

### 4) Scene + manifest (new)

- `scene.schema.json` for per-file scene graphs.
- `scenes_manifest.schema.json` for the list of scene files.

### 5) View Model Schema (engine output)

Add a renderable view model structure:

- `prompt`
- `eligible_actions[]` (full action objects or resolved ids + labels)
- `visible_items[]` (takeable now)
- `visible_npcs[]`

## Example Action (make_tea)

```json
{
  "action_id": "make_tea",
  "label": "Make a cup of tea",
  "when": { "location": "cottage" },
  "effects": [{ "add_item": "tea" }],
  "result_variants": [
    "You fill the kettle and set it on to warm...",
    "You brew a quiet cup, watching the steam rise..."
  ],
  "intent_signature": {
    "keywords": ["tea", "kettle", "brew"],
    "phrases": ["make tea", "cup of tea"]
  }
}
```

## Implementation Plan

1. **Schema additions**
   - Add `actions.schema.json` (new).
   - Add `scene.schema.json` and `scenes_manifest.schema.json`.
   - Add `conditions.schema.json` for `when` clauses.
   - Extend places with `visible_npcs`.
2. **Content updates**
   - Author action objects for cottage.
   - Author per-file scenes and a manifest.
   - Ensure availability is expressed via action eligibility, not item origin.
3. **Engine changes**
   - Eligibility evaluation for actions.
   - Result variant selection (seeded, non-escalating).
4. **UI changes**
   - Intent parser uses `intent_signature`.
   - Multi-intent processing: apply in order, stop on scene exit.
5. **Tests**
   - Schema validation for action objects.
   - Parser acceptance for phrases/keywords.
   - Eligibility gating for journal and location-bound actions.

## Open Questions

- Do we allow action-level cooldowns or once-per-day flags in schema?
- Should `result_variants` be weighted?

## Player State Extensions (Inventory + Visits + Interaction History)

To support item quantities, location visit counts, and non-repeating interactions, extend player state with explicit counters and history. This keeps the engine authoritative and enables eligibility-based variation.

### Proposed Player State Fields

- `inventory_counts`: object map of `item_id -> integer`
- `visit_counts`: object map of `place_id -> integer`
- `seen_interactions`: object map of `interaction_id -> integer` (times seen) or `interaction_id -> string` (last_seen_day)
- `flags`: array of strings (milestones, discoveries, and unlocks)

### Eligibility Usage (Engine)

New or existing content becomes eligible based on:

- `visit_counts[place_id] >= N`
- `seen_interactions[interaction_id]` absent or older than cooldown
- `flags` presence/absence (e.g., `all_portals_opened`)

### Content Example (Conceptual)

``` python
when: ALL(
  LOCATION_IS("town"),
  FLAG_SET("all_portals_opened"),
  NOT_SEEN("town_new_letter_01")
)
```

### Notes

- Inventory quantities replace list-only inventories for authoritative counts.
- `seen_interactions` enables variety by excluding recently used content.
- `flags` represent world milestones without quest framing.

## NPC Visibility Resolution (Always vs Conditional)

To avoid proliferating sub-locations, NPC visibility can be derived from state.

### Data Design

- `places.visible_npcs` lists **always-present** NPCs.
- Conditional NPC visibility is handled via **eligibility rules** (flags, visit counts, or action effects).
- Example: `npc_cat_moss` appears after `leave_location` sets `bakery_left_once`.

### Schema Impact

No new schema fields required if conditional visibility is driven by action/interaction eligibility.
If needed later, we can add a dedicated `npc_visibility` content type; for now, use flags + actions.

## Scenes vs scenes

Scenes replace scenes for graph-based flows. Actions are reusable; scenes own the choice graph.
