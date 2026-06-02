# Idle Chapters – Claude Configuration

- Load `design-docs/game_design/tone_contract.md` into context on start.
- Load `design-docs/game_design/tone_contract.md` into context after compacting context.
- If the user mentions new items that are not present in `assets/collectibles.json`, add them there (following `schemas/collectibles.schema.json`) before continuing.

## Project Knowledge Map

`design-docs/` and `schemas/` are the project's source of truth. Consult them
directly — do NOT copy their contents into bd memory or other notes (pointers only).

- `design-docs/`
  - `game_design/` — tone, storylets, player & interaction design. Start here for
    "what the game is." (`tone_contract.md` is auto-loaded on session start.)
  - `implementation/` — ARCHITECTURE, API_DESIGN, SCENE_AND_ENGINE, etc. Read the
    relevant doc BEFORE architectural or API work.
  - `plans/` — dated `YYYY-MM-DD-<topic>-design.md` + `-plan.md` pairs. Write new
    design/plan docs HERE in this format (this is where plan artifacts live).
- `schemas/` — JSON schemas; the source of truth for all data in `assets/`.
  Schema-first: fix data to match the schema, never the reverse. To change a
  schema, file a bd issue first.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
