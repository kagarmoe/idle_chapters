import pytest

from idle_chapters.services import errors as errors_mod
from idle_chapters.services.errors import GameError, ErrorKind, Effect, Recovery, Signal


class TestGameErrorConstruction:
    def test_create_game_error_with_all_fields(self):
        err = GameError(
            kind=ErrorKind.SESSION_NOT_FOUND,
            effect=Effect.NONE,
            recovery=Recovery.TERMINAL,
            detail="WHAT: No session.\nMEANS: Nothing modified.\nDO: Create new.",
            context={"session_id": "abc-123"},
        )
        assert err.kind == ErrorKind.SESSION_NOT_FOUND
        assert err.effect == Effect.NONE
        assert err.recovery == Recovery.TERMINAL
        assert err.context["session_id"] == "abc-123"

    def test_game_error_is_exception(self):
        err = GameError(
            kind=ErrorKind.SESSION_NOT_FOUND,
            effect=Effect.NONE,
            recovery=Recovery.TERMINAL,
        )
        assert isinstance(err, Exception)

    def test_http_status_mapping(self):
        assert GameError(
            kind=ErrorKind.SESSION_NOT_FOUND,
            effect=Effect.NONE,
            recovery=Recovery.TERMINAL,
        ).http_status == 404

        assert GameError(
            kind=ErrorKind.ENGINE_FAILURE,
            effect=Effect.UNKNOWN,
            recovery=Recovery.ESCALATE,
        ).http_status == 500

        assert GameError(
            kind=ErrorKind.PERSISTENCE_FAILURE,
            effect=Effect.PARTIAL,
            recovery=Recovery.RETRYABLE,
        ).http_status == 503


class TestSignalDerivation:
    """Exhaustive signal derivation per design doc Z535 mapping table."""

    @pytest.mark.parametrize("effect,recovery,expected", [
        # unknown -> always DANGER (state indeterminate)
        (Effect.UNKNOWN, Recovery.ESCALATE, Signal.DANGER),
        (Effect.UNKNOWN, Recovery.RETRYABLE, Signal.DANGER),
        (Effect.UNKNOWN, Recovery.CORRECTABLE, Signal.DANGER),
        (Effect.UNKNOWN, Recovery.TERMINAL, Signal.DANGER),
        # partial + escalate -> DANGER (diverged, manual intervention)
        (Effect.PARTIAL, Recovery.ESCALATE, Signal.DANGER),
        # partial + other -> WARNING (diverged but recoverable)
        (Effect.PARTIAL, Recovery.RETRYABLE, Signal.WARNING),
        (Effect.PARTIAL, Recovery.CORRECTABLE, Signal.WARNING),
        (Effect.PARTIAL, Recovery.TERMINAL, Signal.WARNING),
        # applied (future use: mutation succeeded, downstream issue)
        (Effect.APPLIED, Recovery.ESCALATE, Signal.WARNING),
        (Effect.APPLIED, Recovery.RETRYABLE, Signal.CAUTION),
        (Effect.APPLIED, Recovery.CORRECTABLE, Signal.CAUTION),
        (Effect.APPLIED, Recovery.TERMINAL, Signal.NOTICE),
        # none -> CAUTION or NOTICE
        (Effect.NONE, Recovery.ESCALATE, Signal.CAUTION),
        (Effect.NONE, Recovery.RETRYABLE, Signal.CAUTION),
        (Effect.NONE, Recovery.CORRECTABLE, Signal.CAUTION),
        (Effect.NONE, Recovery.TERMINAL, Signal.NOTICE),
    ])
    def test_signal_derivation(self, effect, recovery, expected):
        # kind is irrelevant to signal derivation; ENGINE_FAILURE is an arbitrary placeholder
        err = GameError(kind=ErrorKind.ENGINE_FAILURE, effect=effect, recovery=recovery)
        assert err.signal == expected, (
            f"({effect}, {recovery}) -> {err.signal}, expected {expected}"
        )


class TestPlayerProjection:
    """Player projection: minimal RFC 9457 (type, title, status)."""

    def test_renders_rfc9457_with_fallback(self):
        """Templates don't exist yet — verify fallback works."""
        err = GameError(
            kind=ErrorKind.INTENT_NO_MATCH,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
            context={"input": "dance", "available_actions": "brew tea, rest"},
        )
        projection = err.project_player()
        assert projection["type"] == "urn:idle-chapters:error:intent_no_match"
        assert projection["status"] == 422
        assert "title" in projection
        assert len(projection["title"]) > 0
        # Player projection must NOT include extension members
        assert "effect" not in projection
        assert "recovery" not in projection
        assert "signal" not in projection

    def test_falls_back_when_no_templates(self):
        err = GameError(
            kind=ErrorKind.INTENT_NO_MATCH,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
            context={},
        )
        projection = err.project_player()
        assert projection["type"] == "urn:idle-chapters:error:intent_no_match"
        assert len(projection["title"]) > 0


class TestDeveloperProjection:
    """Developer projection: full RFC 9457 + Z535 extensions."""

    def test_includes_all_rfc9457_and_extension_fields(self):
        err = GameError(
            kind=ErrorKind.PERSISTENCE_FAILURE,
            effect=Effect.PARTIAL,
            recovery=Recovery.RETRYABLE,
            detail="WHAT: Write failed.\nMEANS: State diverged.\nDO: Retry.",
            context={"session_id": "abc-123"},
        )
        projection = err.project_developer()
        # RFC 9457 required members
        assert projection["type"] == "urn:idle-chapters:error:persistence_failure"
        assert projection["title"] == "Persistence Failure"
        assert projection["status"] == 503
        assert "WHAT" in projection["detail"]
        assert projection["instance"].startswith("urn:idle-chapters:occurrence:")
        # Extension members
        assert projection["effect"] == "partial"
        assert projection["recovery"] == "retryable"
        assert projection["signal"] == "WARNING"
        assert projection["context"]["session_id"] == "abc-123"


class TestPlayerMessage:
    def test_renders_template_with_context(self):
        err = GameError(
            kind=ErrorKind.INTENT_NO_MATCH,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
            context={"input": "dance", "available_actions": "make tea, sit by the fire"},
        )
        assert err.player_message == (
            'Hmm, I\'m not sure what you mean by "dance". '
            "These are the things you could do here: make tea, sit by the fire."
        )

    def test_missing_context_key_uses_fallback(self):
        err = GameError(
            kind=ErrorKind.INTENT_NO_MATCH,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
            context={},
        )
        assert err.player_message == "I didn't quite catch that. What would you like to do?"

    def test_project_player_title_equals_player_message(self):
        err = GameError(
            kind=ErrorKind.SESSION_NOT_FOUND,
            effect=Effect.NONE,
            recovery=Recovery.TERMINAL,
        )
        assert err.project_player()["title"] == err.player_message

    def test_no_template_entry_uses_default_fallback(self, monkeypatch):
        # _load_templates is lru_cache'd, so patch the function itself.
        monkeypatch.setattr(errors_mod, "_load_templates", lambda: {})
        err = GameError(
            kind=ErrorKind.INTENT_NO_MATCH,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
            context={"input": "dance"},
        )
        assert err.player_message == "Something unexpected happened."
