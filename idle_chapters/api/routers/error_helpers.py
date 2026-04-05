"""Shared error helpers for API routers."""
from __future__ import annotations

from typing import NoReturn

from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery


def raise_player_not_found(player_id: str) -> NoReturn:
    """Raise a GameError for a missing player."""
    raise GameError(
        kind=ErrorKind.PLAYER_NOT_FOUND,
        effect=Effect.NONE,
        recovery=Recovery.TERMINAL,
        detail=(
            f"WHAT: No player exists for {player_id}.\n"
            f"MEANS: Nothing was modified.\n"
            f"DO: Create a new player via POST /v1/players."
        ),
        context={"player_id": player_id},
    )


# --- OpenAPI error response examples ---

SESSION_NOT_FOUND_RESPONSES = {
    404: {
        "description": "Session not found",
        "content": {
            "application/json": {
                "examples": {
                    "player": {
                        "summary": "Player projection (default)",
                        "value": {
                            "type": "urn:idle-chapters:error:session_not_found",
                            "title": "That story has found its own ending. You're welcome to begin a new one whenever you'd like.",
                            "status": 404,
                        },
                    },
                    "developer": {
                        "summary": "Developer projection (Accept-Projection: developer)",
                        "value": {
                            "type": "urn:idle-chapters:error:session_not_found",
                            "title": "Session Not Found",
                            "status": 404,
                            "detail": "WHAT: No session exists for abc123.\nMEANS: Nothing was modified.\nDO: Create a new session via POST /v1/sessions.",
                            "instance": "urn:idle-chapters:occurrence:a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "effect": "none",
                            "recovery": "terminal",
                            "signal": "NOTICE",
                            "context": {"session_id": "abc123"},
                        },
                    },
                },
            },
        },
    },
}

ACTION_NOT_ELIGIBLE_RESPONSES = {
    409: {
        "description": "Action not eligible for current state",
        "content": {
            "application/json": {
                "examples": {
                    "player": {
                        "summary": "Player projection (default)",
                        "value": {
                            "type": "urn:idle-chapters:error:action_not_eligible",
                            "title": "That doesn't seem possible right now. Maybe explore a bit more first.",
                            "status": 409,
                        },
                    },
                    "developer": {
                        "summary": "Developer projection (Accept-Projection: developer)",
                        "value": {
                            "type": "urn:idle-chapters:error:action_not_eligible",
                            "title": "Action Not Eligible",
                            "status": 409,
                            "detail": "WHAT: Action gather_herbs failed conditions for session abc123.\nMEANS: State unchanged. Action requires unmet conditions.\nDO: Check eligible actions via GET /v1/sessions/abc123.",
                            "instance": "urn:idle-chapters:occurrence:b2c3d4e5-f6a7-8901-bcde-f12345678901",
                            "effect": "none",
                            "recovery": "correctable",
                            "signal": "CAUTION",
                            "context": {"action_id": "gather_herbs", "session_id": "abc123", "unmet": ["flags_set: visited_garden"]},
                        },
                    },
                },
            },
        },
    },
}

INTENT_NO_MATCH_RESPONSES = {
    422: {
        "description": "No action matched the free-text intent",
        "content": {
            "application/json": {
                "examples": {
                    "player": {
                        "summary": "Player projection (default)",
                        "value": {
                            "type": "urn:idle-chapters:error:intent_no_match",
                            "title": "Hmm, I'm not sure what you mean by \"fly away\". These are the things you could do here: Rest a bit longer, Wake in the cottage.",
                            "status": 422,
                        },
                    },
                    "developer": {
                        "summary": "Developer projection (Accept-Projection: developer)",
                        "value": {
                            "type": "urn:idle-chapters:error:intent_no_match",
                            "title": "Intent No Match",
                            "status": 422,
                            "detail": "WHAT: No action matched intent 'fly away' for session abc123.\nMEANS: State unchanged. Available actions: ['Rest a bit longer', 'Wake in the cottage'].\nDO: Rephrase or choose from eligible actions.",
                            "instance": "urn:idle-chapters:occurrence:c3d4e5f6-a7b8-9012-cdef-123456789012",
                            "effect": "none",
                            "recovery": "correctable",
                            "signal": "CAUTION",
                            "context": {"input": "fly away", "available_actions": "Rest a bit longer, Wake in the cottage", "session_id": "abc123"},
                        },
                    },
                },
            },
        },
    },
}

JOURNAL_PAGE_404_RESPONSES = {
    404: {
        "description": "Session or journal page not found",
        "content": {
            "application/json": {
                "examples": {
                    "session_not_found_player": {
                        "summary": "Session not found — player projection",
                        "value": {
                            "type": "urn:idle-chapters:error:session_not_found",
                            "title": "That story has found its own ending. You're welcome to begin a new one whenever you'd like.",
                            "status": 404,
                        },
                    },
                    "session_not_found_developer": {
                        "summary": "Session not found — developer projection",
                        "value": {
                            "type": "urn:idle-chapters:error:session_not_found",
                            "title": "Session Not Found",
                            "status": 404,
                            "detail": "WHAT: No session exists for abc123.\nMEANS: Nothing was modified.\nDO: Create a new session via POST /v1/sessions.",
                            "instance": "urn:idle-chapters:occurrence:a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "effect": "none",
                            "recovery": "terminal",
                            "signal": "NOTICE",
                            "context": {"session_id": "abc123"},
                        },
                    },
                    "journal_page_not_found_player": {
                        "summary": "Journal page not found — player projection",
                        "value": {
                            "type": "urn:idle-chapters:error:journal_page_not_found",
                            "title": "That page doesn't seem to be in your journal. Perhaps it's from a different chapter.",
                            "status": 404,
                        },
                    },
                    "journal_page_not_found_developer": {
                        "summary": "Journal page not found — developer projection",
                        "value": {
                            "type": "urn:idle-chapters:error:journal_page_not_found",
                            "title": "Journal Page Not Found",
                            "status": 404,
                            "detail": "WHAT: Journal page jp-xyz not found for session abc123.\nMEANS: Nothing was modified.\nDO: List pages via GET /v1/sessions/abc123/journal.",
                            "instance": "urn:idle-chapters:occurrence:e5f6a7b8-c9d0-1234-efab-567890123456",
                            "effect": "none",
                            "recovery": "correctable",
                            "signal": "CAUTION",
                            "context": {"session_id": "abc123", "page_id": "jp-xyz"},
                        },
                    },
                },
            },
        },
    },
}
