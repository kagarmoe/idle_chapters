import pytest

from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery
from idle_chapters.ui import errors as ui_errors


@pytest.fixture(autouse=True)
def reset_verbose():
    yield
    ui_errors.set_verbose(False)


def _caution_error():
    return GameError(
        kind=ErrorKind.ACTION_NOT_ELIGIBLE,
        effect=Effect.NONE,
        recovery=Recovery.CORRECTABLE,
        detail=(
            "WHAT: Action gather_herbs failed conditions.\n"
            "MEANS: State unchanged.\n"
            "DO: Choose an eligible action."
        ),
    )


def test_default_prints_player_message_only(capsys):
    ui_errors.print_error(_caution_error())
    out, err = capsys.readouterr()
    assert "That doesn't seem possible right now" in out
    assert "CAUTION" not in out
    assert err == ""


def test_verbose_prepends_signal_word(capsys):
    ui_errors.set_verbose(True)
    ui_errors.print_error(_caution_error())
    out, _ = capsys.readouterr()
    assert "CAUTION: That doesn't seem possible right now" in out


def test_verbose_writes_three_panel_detail_to_stderr(capsys):
    ui_errors.set_verbose(True)
    ui_errors.print_error(_caution_error())
    out, err = capsys.readouterr()
    # Each panel must begin its own line (scannable), not collapse into a run-on.
    lines = err.splitlines()
    assert any(line.lstrip().startswith("WHAT:") for line in lines)
    assert any(line.lstrip().startswith("MEANS:") for line in lines)
    assert any(line.lstrip().startswith("DO:") for line in lines)
    # Developer detail must never leak onto stdout (player-facing stream).
    assert "WHAT:" not in out


def test_verbose_without_detail_writes_nothing_to_stderr(capsys):
    ui_errors.set_verbose(True)
    err_obj = GameError(
        kind=ErrorKind.SESSION_NOT_FOUND, effect=Effect.NONE, recovery=Recovery.TERMINAL
    )
    ui_errors.print_error(err_obj)
    _, err = capsys.readouterr()
    assert err == ""


def test_invalid_choice_builds_intent_no_match(capsys):
    err_obj = ui_errors.invalid_choice("7", ["make tea", "sit by the fire"])
    assert err_obj.kind == ErrorKind.INTENT_NO_MATCH
    assert err_obj.effect == Effect.NONE
    assert err_obj.recovery == Recovery.CORRECTABLE
    ui_errors.print_error(err_obj)
    out, _ = capsys.readouterr()
    assert '"7"' in out
    assert "make tea, sit by the fire" in out
