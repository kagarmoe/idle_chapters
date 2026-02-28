# API Design (V1)

## Goals

- Keep world content static and schema-validated at boot.
- Treat runtime state as the only mutable data (player/session/journal).
- Support freeform CLI intent parsing without exposing internal engine state.
- Preserve determinism for procedural elements by anchoring to session/state.

## Decisions

1. **Sessions are required for play.**
   - A session holds current scene context, view model, and a stable seed window.
   - This avoids re-rolling procedural elements on reconnect or retry.
2. **World content is read-only via the API.**
   - World data is loaded from JSON on boot (scenes, actions, places, etc.).
   - API exposes view-only endpoints for client tooling and debugging.
3. **Engine is the only writer to player state.**
   - Clients submit intent or explicit action_id; engine applies effects.
4. **Mongo stores runtime state only.**
   - Player state, sessions, journal pages, and interaction history live in Mongo.
   - Static content remains in Git-backed JSON to keep authoring simple.

## Endpoint Sketch

### World (static content)

- `GET /v1/world/manifest`
- `GET /v1/world/places`
- `GET /v1/world/scenes`
- `GET /v1/world/actions`
- `GET /v1/world/collectibles`
- `GET /v1/world/npcs`

### Players

- `POST /v1/players`
  - body: `{ display_name, pronouns_key }`
  - returns: `{ player_id, profile, state }`
- `GET /v1/players/{player_id}`
- `PATCH /v1/players/{player_id}`
  - profile-only updates (no direct state edits)

### Sessions

- `POST /v1/sessions`
  - body: `{ player_id }`
  - returns: `{ session_id, view }`
- `GET /v1/sessions/{session_id}`
  - returns: `{ view, player_id, state_digest }`
- `POST /v1/sessions/{session_id}/intent`
  - body: `{ input: "freeform text" }`
  - returns: `{ view, applied_actions, state_delta, journal_entries }`
- `POST /v1/sessions/{session_id}/action`
  - body: `{ action_id }`
  - returns: `{ view, applied_actions, state_delta, journal_entries }`
- `POST /v1/sessions/{session_id}/peek`
  - returns current view without mutation

### Journal / Inventory (derived)

- `GET /v1/players/{player_id}/inventory`
- `GET /v1/players/{player_id}/journal`

## View Model Contract

```
{
  "prompt": "...",
  "scene_id": "cottage_wake_v1",
  "eligible_actions": [{ "action_id": "...", "label": "..." }],
  "visible_items": ["bag", "mirror"],
  "visible_npcs": ["npc_baker_elin"]
}
```

## State Shape (Mongo)

- `players`
  - profile + canonical state (`inventory_counts`, `visit_counts`, `flags`, etc.)
- `sessions`
  - `player_id`, `scene_id`, `view_cache?`, `updated_at`
- `journal_pages`
  - rendered entries (including inventory page)
- `interaction_history`
  - visit counters + interaction ledger for replay suppression

## Tradeoffs

- **Sessions required**
  - Pro: deterministic procedural results, reconnectable, stable UI.
  - Con: extra write per step and session cleanup/TTL.
- **World content read-only**
  - Pro: Git-native workflow, deterministic testing, no migrations.
  - Con: no live editing without deploy; future content service needed.
- **Engine as sole state writer**
  - Pro: consistent rule enforcement and auditability.
  - Con: slightly higher server complexity; client cannot fast-forward state.

## Open Questions

- Should `/intent` accept multi-intent arrays or only raw input?
- Should view models include action `intent_signature` for client hints?
- Do we want a `/v1/world/export` endpoint for offline play?
