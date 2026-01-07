# CLI Intent Parsing & Eligibility (Draft)

## Purpose
Define how freeform CLI input maps to eligible in-world actions without violating the schema-first design contract. This document assumes the engine remains the single source of truth for eligibility and effects.

## Principles (Schema-First)
- **Content is data**: actions and scenes are declarative objects that validate against schemas.
- **Engine decides eligibility**: the UI never “unlocks” actions.
- **Parsing is interpretation**: user input maps to **intent**, which the engine validates against eligible actions.
- **Procedural generation is content-shaped and optional**: generators can supply candidates but are not required for the engine to operate.

## High-Level Flow
1. **Engine** produces a renderable view:
   - location, prompt text
   - `eligible_actions[]`
   - `visible_items[]`
   - `visible_npcs[]`
2. **UI** renders prompt and waits for input.
3. **Parser** maps input → `intent` (or multiple intents).
4. **Engine** resolves intent against `eligible_actions[]`:
   - accepts if eligible
   - rejects with a gentle fallback if not eligible
5. **Engine** applies effects and returns next view.

## CLI Commands (Out-of-World)
These are handled by the UI and do not go through engine eligibility:
- **"What can I do?"** → list current eligible actions (labels).
- **"What is here?"** → list visible items (only those takeable now) and visible NPCs.
- **"Help"** → repeat how to ask for actions or describe intent.

## Intent Parsing (Freeform Input)
### Goals
- Minimal friction: accept varied phrasing.
- No punishment for order: if an intent is eligible, it should work.
- Multi-intent: allow “I’ll make tea and then look around.”

### Approach
1. Normalize input:
   - lowercase, trim, remove punctuation
2. Split into clauses:
   - separators: “and”, “then”, commas
3. Match clauses to **intent signatures**.

### Intent Signatures (Example)
Each action can define:
- `action_id`
- `keywords[]`
- `phrases[]` (multi-token matches)
- `aliases[]` (optional)

Example:
- `make_tea`: keywords = ["tea", "brew", "kettle"], phrases = ["make tea", "cup of tea"]
- `look_around`: keywords = ["look", "around", "explore"], phrases = ["look around", "have a look"]
- `rest_longer`: keywords = ["linger", "rest", "stay", "sleep"]

### Matching Rules
- Phrase match > keyword match.
- Ignore intents that are not eligible right now.
- If a clause maps to multiple eligible intents, choose the most specific:
  - phrase match > keyword match
  - longer phrase > shorter phrase

### Multi-Intent Execution
Process clauses in order:
1. Resolve each clause to an eligible action.
2. Execute actions sequentially, updating state between them.
3. Stop if an action ends the scene (e.g., “head to town”).

## Eligibility & Gating
Eligibility is data-driven and evaluated in the engine:
- `when` conditions (location, flags, inventory_counts, visit_counts, time)
- cooldowns / once-per-visit
- mutual exclusivity (if applicable)

**Example gating:**
`pick_up_journal` is eligible only after `cottage_inside` is true.

## Discoverability
The game must be safe when the player doesn’t know what to type:
- If input doesn’t match any eligible action:
  - respond with a gentle fallback
  - hint: “You can ask ‘What can I do?’ or ‘What is here?’”

## Repetition & Variation
Actions may be repeatable, with **variant text**:
- Content includes `result_variants[]`
- Engine selects a variant (seeded randomness)
- No escalation; variations should be ambient.

## Data Structures (Conceptual)
### Action (content-shaped)
```
Action {
  action_id
  label
  when
  effects
  result_variants[]
  intent_signature {
    keywords[]
    phrases[]
  }
}
```

### Scene (content-shaped)
```
Scene {
  scene_id
  place_id
  entry_node
  nodes[] {
    node_id
    action_ref
    choices[]
  }
}
```

### Engine view model
```
View {
  location_id
  prompt
  eligible_actions[]
  visible_items[]
  visible_npcs[]
}
```

## Notes on Schema Design
- Actions, scenes, and intent signatures should be part of validated schema files.
- CLI parsing should operate **only** on schema-backed fields.
- Scenes are stored per-file with a manifest.
- Places only declare `visible_npcs` for always-present NPCs.

## Alignment with Design Docs
- Engine is deterministic and authoritative.
- UI is thin and does not encode rules.
- Procedural generation supplies optional content only.
- Tone contract applies to all text variants.
