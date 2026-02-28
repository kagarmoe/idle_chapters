# Idle Chapters – Claude Configuration

- Load `dev/game_design/tone_contract.md` into context on start.
- Load `dev/game_design/tone_contract.md` into context after compacting context.
- If the user mentions new items that are not present in `assets/collectibles.json`, add them there (following `schemas/collectibles.schema.json`) before continuing.
- Schema-first design: JSON schemas in `schemas/` are the source of truth. If data in `assets/` fails validation, fix the data to conform to the schema. Do not modify schemas to accommodate invalid data. If a schema genuinely needs updating, create an issue to discuss the change.
