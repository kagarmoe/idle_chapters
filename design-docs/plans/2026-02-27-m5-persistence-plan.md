# M5: MongoDB Persistence — Implementation Plan

> **For Claude:**

**Goal:** Add MongoDB persistence so sessions, player state, journal pages, and events survive across app restarts.

**Architecture:** Thin store classes (`StateStore`, `JournalStore`, `EventStore`) wrapping a `get_db()` singleton. Field names map from domain model to MongoDB schema (schema wins). Standalone layer — API routers adopt in M6.

**Tech Stack:** Python 3.10+, pymongo 4.x, pytest, dataclasses

---

### Task 1: Connection Layer (`mongo.py`)

**Files:**
- Modify: `app/persistence/mongo.py`

**Step 1: Write `get_db()` implementation**

Replace the TODO stub with:

```python
from __future__ import annotations

import os

from pymongo import MongoClient
from pymongo.database import Database


_CLIENT: MongoClient | None = None


def get_db() -> Database:
    """Return the MongoDB database, creating the client on first call."""
    global _CLIENT
    if _CLIENT is None:
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        _CLIENT = MongoClient(mongo_url)
    db_name = os.getenv("MONGO_DB", "idle_chapters")
    return _CLIENT[db_name]
```

This mirrors `app/api/db.py` exactly — same env vars (`MONGO_URL`, `MONGO_DB`), same defaults.

**Step 2: Commit**

```bash
git add app/persistence/mongo.py
git commit -m "feat(persistence): Implement get_db() connection layer"
```

---

### Task 2: StateStore — Failing Test

**Files:**
- Modify: `tests/test_persistence.py`

**Step 1: Update the existing state store test**

The existing test is mostly correct but uses `MONGO_URI` (should be `MONGO_URL`) and compares via `_state_to_dict` which won't handle the `set` -> `list` -> `set` round-trip correctly (set becomes list in `__dict__`). Rewrite:

```python
import os
import uuid

import pytest


@pytest.fixture
def unique_session_id():
    """Generate a unique session ID per test to avoid cross-test pollution."""
    return f"test_{uuid.uuid4().hex[:12]}"


@pytest.mark.skipif(os.getenv("MONGO_URL") is None, reason="MONGO_URL not set")
def test_state_store_round_trip(unique_session_id) -> None:
    from idle_chapters.domain.state import PlayerState
    from idle_chapters.persistence.state_store import StateStore

    store = StateStore()
    state = PlayerState(
        session_id=unique_session_id,
        current_place_id="cottage_home",
        inventory={"item_1": 1},
        flags={"flag_a"},
        time_tick=1,
    )

    store.upsert_state(unique_session_id, state)
    loaded = store.get_state(unique_session_id)

    assert loaded is not None
    assert loaded.session_id == state.session_id
    assert loaded.current_place_id == state.current_place_id
    assert loaded.inventory == state.inventory
    assert loaded.flags == state.flags
    assert loaded.time_tick == state.time_tick
    assert loaded.visit_counts == state.visit_counts
    assert loaded.seen_interactions == state.seen_interactions
    assert loaded.current_scene_id == state.current_scene_id
    assert loaded.current_node_id == state.current_node_id


@pytest.mark.skipif(os.getenv("MONGO_URL") is None, reason="MONGO_URL not set")
def test_state_store_returns_none_for_missing(unique_session_id) -> None:
    from idle_chapters.persistence.state_store import StateStore

    store = StateStore()
    assert store.get_state(unique_session_id) is None


@pytest.mark.skipif(os.getenv("MONGO_URL") is None, reason="MONGO_URL not set")
def test_state_store_upsert_overwrites(unique_session_id) -> None:
    from idle_chapters.domain.state import PlayerState
    from idle_chapters.persistence.state_store import StateStore

    store = StateStore()
    state1 = PlayerState(
        session_id=unique_session_id,
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )
    store.upsert_state(unique_session_id, state1)

    state2 = PlayerState(
        session_id=unique_session_id,
        current_place_id="forest_clearing",
        inventory={"key": 1},
        flags={"found_key"},
        time_tick=3,
    )
    store.upsert_state(unique_session_id, state2)

    loaded = store.get_state(unique_session_id)
    assert loaded.current_place_id == "forest_clearing"
    assert loaded.inventory == {"key": 1}
    assert loaded.flags == {"found_key"}
    assert loaded.time_tick == 3
```

**Step 2: Run tests to verify they fail**

Run: `MONGO_URL=mongodb://localhost:27017 pytest tests/test_persistence.py -v`
Expected: FAIL — `StateStore` has no `upsert_state`/`get_state` methods (stub file)

**Step 3: Commit**

```bash
git add tests/test_persistence.py
git commit -m "test(persistence): Update state store tests for M5"
```

---

### Task 3: StateStore — Implementation

**Files:**
- Modify: `app/persistence/state_store.py`

**Step 1: Implement StateStore**

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from idle_chapters.persistence.mongo import get_db

if TYPE_CHECKING:
    from pymongo.database import Database

    from idle_chapters.domain.state import PlayerState


class StateStore:
    def __init__(self, db: Database | None = None):
        self._db = db

    @property
    def _collection(self):
        db = self._db or get_db()
        return db["sessions"]

    def upsert_state(self, session_id: str, state: PlayerState) -> None:
        """Persist player state into the sessions collection.

        Maps domain field names to schema field names (schema wins).
        """
        doc = {
            "state": {
                "current_location": state.current_place_id,
                "inventory_counts": dict(state.inventory),
                "flags": sorted(state.flags),
                "time_tick": state.time_tick,
                "visit_counts": dict(state.visit_counts),
                "seen_interactions": dict(state.seen_interactions),
                "current_scene_id": state.current_scene_id,
                "current_node_id": state.current_node_id,
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._collection.update_one(
            {"session_id": session_id},
            {"$set": doc, "$setOnInsert": {"session_id": session_id, "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )

    def get_state(self, session_id: str) -> PlayerState | None:
        """Load player state from the sessions collection.

        Maps schema field names back to domain field names.
        Returns None if session not found.
        """
        from idle_chapters.domain.state import PlayerState

        doc = self._collection.find_one({"session_id": session_id})
        if doc is None:
            return None

        s = doc.get("state", {})
        return PlayerState(
            session_id=session_id,
            current_place_id=s.get("current_location", ""),
            inventory=dict(s.get("inventory_counts") or {}),
            flags=set(s.get("flags") or []),
            time_tick=s.get("time_tick", 0),
            visit_counts=dict(s.get("visit_counts") or {}),
            seen_interactions=dict(s.get("seen_interactions") or {}),
            current_scene_id=s.get("current_scene_id"),
            current_node_id=s.get("current_node_id"),
        )
```

**Step 2: Run tests to verify they pass**

Run: `MONGO_URL=mongodb://localhost:27017 pytest tests/test_persistence.py::test_state_store_round_trip tests/test_persistence.py::test_state_store_returns_none_for_missing tests/test_persistence.py::test_state_store_upsert_overwrites -v`
Expected: 3 PASSED

**Step 3: Commit**

```bash
git add app/persistence/state_store.py
git commit -m "feat(persistence): Implement StateStore with field mapping"
```

---

### Task 4: JournalStore — Failing Test

**Files:**
- Modify: `tests/test_persistence.py`

**Step 1: Update journal store test and add new tests**

Replace the existing `test_journal_store_round_trip` and add tests. The page shape matches `JournalPage.to_dict()` — a flat dict with `page_id`, `place_id`, `entry_type`, `mood`, `need`, `ingredients`, `prompt`, `body`, `date`, `tags`.

Add these tests after the state store tests in `tests/test_persistence.py`:

```python
@pytest.mark.skipif(os.getenv("MONGO_URL") is None, reason="MONGO_URL not set")
def test_journal_store_round_trip(unique_session_id) -> None:
    from idle_chapters.persistence.journal_store import JournalStore

    store = JournalStore()
    page = {
        "page_id": "page_1",
        "date": "2026-02-27",
        "place_id": "cottage_home",
        "entry_type": "tea",
        "mood": "calm",
        "need": "rest",
        "ingredients": ["chamomile_flower"],
        "prompt": "What softened today?",
        "body": "A small pause.",
        "tags": ["tea"],
    }

    store.append_page(unique_session_id, page)
    pages = store.list_pages(unique_session_id)

    assert len(pages) >= 1
    assert any(p.get("page_id") == "page_1" for p in pages)

    loaded = store.get_page(unique_session_id, "page_1")
    assert loaded is not None
    assert loaded["page_id"] == "page_1"
    assert loaded["body"] == "A small pause."
    assert loaded["entry_type"] == "tea"


@pytest.mark.skipif(os.getenv("MONGO_URL") is None, reason="MONGO_URL not set")
def test_journal_store_list_ordering(unique_session_id) -> None:
    from idle_chapters.persistence.journal_store import JournalStore

    store = JournalStore()
    store.append_page(unique_session_id, {"page_id": "p1", "body": "first"})
    store.append_page(unique_session_id, {"page_id": "p2", "body": "second"})

    pages = store.list_pages(unique_session_id)
    page_ids = [p["page_id"] for p in pages]
    assert page_ids.index("p1") < page_ids.index("p2")


@pytest.mark.skipif(os.getenv("MONGO_URL") is None, reason="MONGO_URL not set")
def test_journal_store_get_missing_returns_none(unique_session_id) -> None:
    from idle_chapters.persistence.journal_store import JournalStore

    store = JournalStore()
    assert store.get_page(unique_session_id, "nonexistent") is None
```

**Step 2: Run tests to verify they fail**

Run: `MONGO_URL=mongodb://localhost:27017 pytest tests/test_persistence.py -k journal -v`
Expected: FAIL — `JournalStore` has no methods

**Step 3: Commit**

```bash
git add tests/test_persistence.py
git commit -m "test(persistence): Add journal store tests for M5"
```

---

### Task 5: JournalStore — Implementation

**Files:**
- Modify: `app/persistence/journal_store.py`

**Step 1: Implement JournalStore**

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from idle_chapters.persistence.mongo import get_db

if TYPE_CHECKING:
    from pymongo.database import Database


class JournalStore:
    def __init__(self, db: Database | None = None):
        self._db = db

    @property
    def _collection(self):
        db = self._db or get_db()
        return db["journal_pages"]

    def append_page(self, session_id: str, page: dict) -> None:
        """Append a journal page for the given session."""
        doc = dict(page)
        doc["session_id"] = session_id
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        self._collection.insert_one(doc)

    def list_pages(self, session_id: str) -> list[dict]:
        """Return all journal pages for a session, ordered by creation time."""
        cursor = self._collection.find(
            {"session_id": session_id},
            {"_id": 0},
        ).sort("created_at", 1)
        return list(cursor)

    def get_page(self, session_id: str, page_id: str) -> dict | None:
        """Return a single journal page by page_id within a session."""
        doc = self._collection.find_one(
            {"session_id": session_id, "page_id": page_id},
            {"_id": 0},
        )
        return doc
```

**Step 2: Run tests to verify they pass**

Run: `MONGO_URL=mongodb://localhost:27017 pytest tests/test_persistence.py -k journal -v`
Expected: 3 PASSED

**Step 3: Commit**

```bash
git add app/persistence/journal_store.py
git commit -m "feat(persistence): Implement JournalStore"
```

---

### Task 6: EventStore — Failing Test

**Files:**
- Modify: `tests/test_persistence.py`

**Step 1: Add event store tests**

Add these tests to `tests/test_persistence.py`:

```python
@pytest.mark.skipif(os.getenv("MONGO_URL") is None, reason="MONGO_URL not set")
def test_event_store_round_trip(unique_session_id) -> None:
    from idle_chapters.persistence.event_store import EventStore

    store = EventStore()
    event = {
        "event_type": "step",
        "data": {"command": "enter", "place_id": "cottage_home", "seed": 123},
    }

    store.append_event(unique_session_id, event)
    events = store.list_events(unique_session_id)

    assert len(events) >= 1
    assert events[0]["event_type"] == "step"
    assert events[0]["data"]["command"] == "enter"
    assert "created_at" in events[0]


@pytest.mark.skipif(os.getenv("MONGO_URL") is None, reason="MONGO_URL not set")
def test_event_store_ordering(unique_session_id) -> None:
    from idle_chapters.persistence.event_store import EventStore

    store = EventStore()
    store.append_event(unique_session_id, {"event_type": "enter", "data": {}})
    store.append_event(unique_session_id, {"event_type": "choose", "data": {}})

    events = store.list_events(unique_session_id)
    types = [e["event_type"] for e in events]
    assert types.index("enter") < types.index("choose")
```

**Step 2: Run tests to verify they fail**

Run: `MONGO_URL=mongodb://localhost:27017 pytest tests/test_persistence.py -k event -v`
Expected: FAIL — `EventStore` has no methods

**Step 3: Commit**

```bash
git add tests/test_persistence.py
git commit -m "test(persistence): Add event store tests for M5"
```

---

### Task 7: EventStore — Implementation

**Files:**
- Modify: `app/persistence/event_store.py`

**Step 1: Implement EventStore**

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from idle_chapters.persistence.mongo import get_db

if TYPE_CHECKING:
    from pymongo.database import Database


class EventStore:
    def __init__(self, db: Database | None = None):
        self._db = db

    @property
    def _collection(self):
        db = self._db or get_db()
        return db["events"]

    def append_event(self, session_id: str, event: dict) -> None:
        """Append an event to the event log for a session."""
        doc = dict(event)
        doc["session_id"] = session_id
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        self._collection.insert_one(doc)

    def list_events(self, session_id: str) -> list[dict]:
        """Return all events for a session, ordered by creation time."""
        cursor = self._collection.find(
            {"session_id": session_id},
            {"_id": 0},
        ).sort("created_at", 1)
        return list(cursor)
```

**Step 2: Run tests to verify they pass**

Run: `MONGO_URL=mongodb://localhost:27017 pytest tests/test_persistence.py -k event -v`
Expected: 2 PASSED

**Step 3: Commit**

```bash
git add app/persistence/event_store.py
git commit -m "feat(persistence): Implement EventStore"
```

---

### Task 8: Full Suite Verification

**Step 1: Run all persistence tests**

Run: `MONGO_URL=mongodb://localhost:27017 pytest tests/test_persistence.py -v`
Expected: 8 PASSED (3 state + 3 journal + 2 event)

**Step 2: Run full test suite for regressions**

Run: `pytest tests/ --ignore=tests/test_api.py -v`
Expected: No regressions. Persistence tests skip (no MONGO_URL in CI).

**Step 3: Final commit with all files**

```bash
git status  # verify only M5 files changed
```

If any uncommitted M5 files remain, stage and commit them.
