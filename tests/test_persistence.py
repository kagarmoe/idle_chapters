import os
import uuid

import pytest

mongo = pytest.mark.skipif(os.getenv("MONGO_URL") is None, reason="MONGO_URL not set")


@pytest.fixture
def unique_session_id():
    """Generate a unique session ID per test to avoid cross-test pollution."""
    return f"test_{uuid.uuid4().hex[:12]}"


@mongo
def test_mongo_connectivity() -> None:
    """Smoke test: can we reach MongoDB and run a command?"""
    from app.persistence.mongo import get_db

    db = get_db()
    result = db.command("ping")
    assert result.get("ok") == 1.0


@mongo
def test_state_store_round_trip(unique_session_id) -> None:
    from app.domain.state import PlayerState
    from app.persistence.state_store import StateStore

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


@mongo
def test_state_store_returns_none_for_missing(unique_session_id) -> None:
    from app.persistence.state_store import StateStore

    store = StateStore()
    assert store.get_state(unique_session_id) is None


@mongo
def test_state_store_upsert_overwrites(unique_session_id) -> None:
    from app.domain.state import PlayerState
    from app.persistence.state_store import StateStore

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


@mongo
def test_journal_store_round_trip(unique_session_id) -> None:
    from app.persistence.journal_store import JournalStore

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


@mongo
def test_journal_store_list_ordering(unique_session_id) -> None:
    from app.persistence.journal_store import JournalStore

    store = JournalStore()
    store.append_page(unique_session_id, {"page_id": "p1", "body": "first"})
    store.append_page(unique_session_id, {"page_id": "p2", "body": "second"})

    pages = store.list_pages(unique_session_id)
    page_ids = [p["page_id"] for p in pages]
    assert page_ids.index("p1") < page_ids.index("p2")


@mongo
def test_journal_store_get_missing_returns_none(unique_session_id) -> None:
    from app.persistence.journal_store import JournalStore

    store = JournalStore()
    assert store.get_page(unique_session_id, "nonexistent") is None


@mongo
def test_event_store_round_trip(unique_session_id) -> None:
    from app.persistence.event_store import EventStore

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


@mongo
def test_event_store_ordering(unique_session_id) -> None:
    from app.persistence.event_store import EventStore

    store = EventStore()
    store.append_event(unique_session_id, {"event_type": "enter", "data": {}})
    store.append_event(unique_session_id, {"event_type": "choose", "data": {}})

    events = store.list_events(unique_session_id)
    types = [e["event_type"] for e in events]
    assert types.index("enter") < types.index("choose")
