# Idle Chapters – Claude Configuration

- Load `dev/game_design/tone_contract.md` into context on start.
- Load `dev/game_design/tone_contract.md` into context after compacting context.
- If the user mentions new items that are not present in `assets/collectibles.json`, add them there (following `schemas/collectibles.schema.json`) before continuing.
