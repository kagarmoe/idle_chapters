# M5: MongoDB Persistence — Design

## Context

Milestones 0-4 are complete: content loading, scene generation, journal rendering, and the domain engine all work. Game state currently lives only in memory — a restart loses everything. M5 adds MongoDB persistence so sessions, player state, and journal pages survive across app restarts.

## Design Decisions

1. **Standalone layer** — `app/persistence/` is self-contained. The existing API routers (`app/api/`) keep their inline DB calls for now. M6 will refactor routers to use the persistence stores.
2. **Schema wins for field names** — The persistence layer maps domain model fields to MongoDB schema names when writing (e.g., `inventory` -> `inventory_counts`, `current_place_id` -> `current_location`). Schemas are the source of truth for document shape.
3. **Thin store classes** — `StateStore`, `JournalStore`, `EventStore` wrap `get_db()`. No abstract protocols or repository pattern.
4. **Real MongoDB tests only** — Tests skip when `MONGO_URL` is unset. No mongomock.
5. **Event store included** — Append-only log for debugging and replay.

## Architecture

```
app/persistence/
  mongo.py          -- get_db() singleton
  state_store.py    -- StateStore class
  journal_store.py  -- JournalStore class
  event_store.py    -- EventStore class
```

### Connection Layer (`mongo.py`)

- `get_db() -> Database` — singleton MongoClient
- Reads `MONGO_URL` env var (default: `mongodb://localhost:27017`)
- Database name from `MONGO_DB` env var (default: `idle_chapters`)
- Mirrors `app/api/db.py` (same env vars, same defaults)

### StateStore (`state_store.py`)

Collection: `sessions`

```python
class StateStore:
    def __init__(self, db=None):       # defaults to get_db()
    def upsert_state(session_id, state: PlayerState) -> None
    def get_state(session_id) -> PlayerState | None
```

Field mapping (domain -> MongoDB document):

| Domain (`PlayerState`)  | MongoDB (`state.*`)     | Transform        |
|-------------------------|-------------------------|------------------|
| `current_place_id`      | `current_location`      | rename           |
| `inventory` (dict)      | `inventory_counts`      | rename           |
| `flags` (set)           | `flags` (array)         | list() / set()   |
| `time_tick`             | `time_tick`             | passthrough      |
| `visit_counts`          | `visit_counts`          | passthrough      |
| `seen_interactions`     | `seen_interactions`     | passthrough      |
| `current_scene_id`      | `current_scene_id`      | passthrough      |
| `current_node_id`       | `current_node_id`       | passthrough      |

State is stored as a nested `state` sub-document within the session document, matching `sessions.schema.json`. `upsert_state` also sets `updated_at`.

### JournalStore (`journal_store.py`)

Collection: `journal_pages`

```python
class JournalStore:
    def __init__(self, db=None):
    def append_page(session_id, page: dict) -> None
    def list_pages(session_id) -> list[dict]
    def get_page(session_id, page_id) -> dict | None
```

Pages are stored as flat dicts matching `JournalPage.to_dict()` output plus `session_id` and `created_at`. Ordered by `created_at` in `list_pages`.

### EventStore (`event_store.py`)

Collection: `events`

```python
class EventStore:
    def __init__(self, db=None):
    def append_event(session_id, event: dict) -> None
    def list_events(session_id) -> list[dict]
```

Append-only log. Each document: `session_id`, `event_type`, `data`, `created_at`.

## Tests

File: `tests/test_persistence.py`

- Fix env var from `MONGO_URI` to `MONGO_URL`
- State store round-trip: create PlayerState, upsert, get, verify equality
- Journal store round-trip: append page, list pages, get page by ID
- Event store round-trip: append event, list events
- All tests gated by `skipif MONGO_URL is None`
- Update journal test to use flat dict shape (no frontmatter wrapper)

## Acceptance Criteria

From V1 plan:
- Create session -> state persists
- Step -> journal page appended
- Reload -> state + pages match
- Session data is portable across app restarts
