import os

import pytest


def _state_to_dict(state):
    if isinstance(state, dict):
        return state
    if hasattr(state, "model_dump"):
        return state.model_dump()
    if hasattr(state, "dict"):
        return state.dict()
    return state.__dict__


@pytest.mark.skipif(os.getenv("MONGO_URI") is None, reason="MONGO_URI not set")
def test_state_store_round_trip() -> None:
    from app.domain.state import PlayerState
    from app.persistence.state_store import StateStore

    store = StateStore()
    session_id = "session_test"
    state = PlayerState(
        session_id=session_id,
        current_place_id="cottage_home",
        inventory={"item_1": 1},
        flags={"flag_a"},
        time_tick=1,
    )

    store.upsert_state(session_id, state)
    loaded = store.get_state(session_id)

    assert _state_to_dict(loaded) == _state_to_dict(state)


@pytest.mark.skipif(os.getenv("MONGO_URI") is None, reason="MONGO_URI not set")
def test_journal_store_round_trip() -> None:
    from app.persistence.journal_store import JournalStore

    store = JournalStore()
    session_id = "session_test"
    page = {
        "page_id": "page_1",
        "frontmatter": {"entry_type": "tea", "place_id": "cottage_home"},
        "body": "A small pause.",
    }

    store.append_page(session_id, page)
    pages = store.list_pages(session_id)

    assert any(p.get("page_id") == "page_1" for p in pages)
    loaded = store.get_page(session_id, "page_1")
    assert loaded.get("page_id") == "page_1"
