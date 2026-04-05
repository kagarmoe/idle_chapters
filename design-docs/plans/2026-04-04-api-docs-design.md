# API Documentation with Request/Response Examples

## Status

**Approved design** — ready for implementation planning.

## Problem

The API now returns RFC 9457 structured errors with player and developer projections, but the auto-generated OpenAPI docs show no examples. A developer looking at `/docs` sees response schemas but no realistic request/response pairs, and no indication of the dual-projection error format.

## Design

Add OpenAPI examples at two levels:

1. **Success examples on Pydantic models** via `model_config` with `json_schema_extra`. Shows realistic game data from `assets/`.
2. **Error examples on route decorators** via the `responses` parameter. Each error endpoint shows both player and developer projections inline.

### Success Examples (Pydantic Models)

Each response model in `idle_chapters/api/models.py` gets a `model_config` with an example using real game content (cottage_home, tea, journal pages, etc.).

Models to update:
- `ViewModel`
- `SessionCreateResponse`
- `SessionGetResponse`
- `StepResponse`
- `PlayerResponse`
- `ViewAction`

### Error Examples (Route Decorators)

Each endpoint that can return an error gets a `responses` dict on the decorator. Every error status code includes two named examples: `player` (default projection) and `developer` (full RFC 9457 + Z535).

Player example shape:
```json
{
    "type": "urn:idle-chapters:error:{kind}",
    "title": "Tone-contract compliant message...",
    "status": 404
}
```

Developer example shape:
```json
{
    "type": "urn:idle-chapters:error:{kind}",
    "title": "Human Readable Title",
    "status": 404,
    "detail": "WHAT: ...\nMEANS: ...\nDO: ...",
    "instance": "urn:idle-chapters:occurrence:{uuid}",
    "effect": "none",
    "recovery": "terminal",
    "signal": "NOTICE",
    "context": { ... }
}
```

### Endpoint Coverage

| Router | Endpoint | Success Example | Error Examples |
|---|---|---|---|
| sessions | `POST /v1/sessions` | SessionCreateResponse | — |
| sessions | `GET /v1/sessions/{id}` | SessionGetResponse | 404 session_not_found |
| sessions | `POST /v1/sessions/{id}/enter` | StepResponse | 404 session_not_found |
| sessions | `POST /v1/sessions/{id}/action` | StepResponse | 404 session_not_found, 409 action_not_eligible |
| sessions | `POST /v1/sessions/{id}/intent` | StepResponse | 404 session_not_found, 422 intent_no_match |
| sessions | `GET /v1/sessions/{id}/journal` | journal list | 404 session_not_found |
| sessions | `GET /v1/sessions/{id}/journal/{page_id}` | journal page | 404 session_not_found, 404 journal_page_not_found |
| players | `POST /v1/players` | PlayerResponse | — |
| players | `GET /v1/players/{id}` | PlayerResponse | 404 player_not_found |
| players | `PATCH /v1/players/{id}` | PlayerResponse | 404 player_not_found |
| journal | `GET /v1/players/{id}/inventory` | inventory dict | 404 player_not_found |
| journal | `GET /v1/players/{id}/journal` | journal list | 404 player_not_found |
| world | `GET /v1/world/manifest` | manifest dict | — |
| world | `GET /v1/world/places` | places list | — |
| world | `GET /v1/world/scenes` | scenes list | — |
| world | `GET /v1/world/actions` | actions list | — |
| world | `GET /v1/world/collectibles` | collectibles list | — |
| world | `GET /v1/world/npcs` | npcs list | — |

### Files Changed

- `idle_chapters/api/models.py` — add `model_config` with examples to response models
- `idle_chapters/api/routers/sessions.py` — add `responses` to error endpoints
- `idle_chapters/api/routers/players.py` — add `responses` to error endpoints
- `idle_chapters/api/routers/journal.py` — add `responses` to error endpoints
- `idle_chapters/api/routers/world.py` — add success examples (response descriptions)
- `docs/openapi.json` — regenerated

### Data Sources

All success examples use real content from:
- `assets/places.json` — place IDs, zone IDs
- `assets/actions.json` — action IDs, labels
- `assets/collectibles.json` — item names
- `assets/journal_templates.json` — entry types, prompts
- `schemas/journal_page.schema.json` — journal page structure

Error examples use templates from `assets/error_templates.json`.

## Acceptance Criteria

- Every endpoint has at least one success example with real game data
- Every error endpoint shows both player and developer projection examples
- Examples render correctly in `/docs` (Swagger UI)
- Error examples use RFC 9457 structure with Z535 signal words
- No tone contract violations in player projection examples
- OpenAPI spec regenerated and committed
