# Agent Instructions

## Project Knowledge Map

`design-docs/` and `schemas/` are the project's source of truth. Consult them
directly — do NOT copy their contents into memory or other notes (pointers only).

- `design-docs/`
  - `game_design/` — tone, storylets, player & interaction design. Start here for
    "what the game is." (`tone_contract.md` is auto-loaded on session start.)
  - `implementation/` — ARCHITECTURE, API_DESIGN, SCENE_AND_ENGINE, etc. Read the
    relevant doc BEFORE architectural or API work.
  - `plans/` — dated `YYYY-MM-DD-<topic>-design.md` + `-plan.md` pairs. Write new
    design/plan docs HERE in this format (this is where plan artifacts live).
- `schemas/` — JSON schemas; the source of truth for all data in `assets/`.
  Schema-first: fix data to match the schema, never the reverse. To change a
  schema, get the user's approval first.

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var
