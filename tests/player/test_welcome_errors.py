import json
import sys

import pytest

from idle_chapters import main as main_mod
from idle_chapters.scenes import welcome
from idle_chapters.ui import errors as ui_errors


@pytest.fixture(autouse=True)
def reset_verbose():
    yield
    ui_errors.set_verbose(False)


def test_invalid_pronoun_choice_uses_tone_template(monkeypatch, capsys):
    answers = iter(["9", "6"])  # one bad choice, then exit
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    result = welcome._select_pronouns()
    assert result is None
    out, _ = capsys.readouterr()
    assert 'Hmm, I\'m not sure what you mean by "9"' in out
    assert "Please choose a valid option" not in out


def test_save_player_io_error_uses_persistence_template(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise IOError("disk full")

    # Patch the module attribute (shadows the builtin inside welcome.py only)
    # so the patched open cannot leak into GameError's lazy template load.
    monkeypatch.setattr(welcome, "open", boom, raising=False)
    welcome.save_player({"player_info": {"display_name": "Fern"}})
    out, _ = capsys.readouterr()
    assert "Your story was briefly interrupted" in out
    assert "Error saving file" not in out


def test_save_players_io_error_uses_persistence_template(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise IOError("disk full")

    monkeypatch.setattr(welcome, "open", boom, raising=False)
    welcome._save_players([{"player_info": {"display_name": "Fern"}}])
    out, _ = capsys.readouterr()
    assert "Your story was briefly interrupted" in out
    assert "Error saving file" not in out


def test_load_players_non_list_uses_reworded_notice(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "players.json"
    bad.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    monkeypatch.setattr(welcome, "PLAYERS_FILE", str(bad))
    result = welcome._load_players()
    assert result == []
    out, _ = capsys.readouterr()
    normalized = " ".join(out.split())  # wrap_text inserts line breaks/indent
    assert "Those pages seem to belong to a different story. Let's begin a new one." in normalized
    assert "Existing player data is invalid" not in out
    assert "Error loading player file" not in out


def test_load_player_invalid_json_uses_reworded_notice(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "player.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    monkeypatch.setattr(welcome, "PLAYER_FILE", str(bad))
    result = welcome.load_player()
    assert result == {}
    out, _ = capsys.readouterr()
    normalized = " ".join(out.split())  # wrap_text inserts line breaks/indent
    assert "Your earlier pages are resting somewhere else. A fresh page is ready." in normalized
    assert "Existing player data is invalid" not in out
    assert "Error loading player file" not in out


def test_validate_player_detail_silent_when_not_verbose(capsys):
    assert welcome._validate_player({"bogus": True}) is False
    _, err = capsys.readouterr()
    assert err == ""


def test_validate_player_detail_on_stderr_when_verbose(capsys):
    ui_errors.set_verbose(True)
    assert welcome._validate_player({"bogus": True}) is False
    _, err = capsys.readouterr()
    assert "failed schema validation" in err


def test_select_player_invalid_menu_choice_uses_intent_template(monkeypatch, capsys):
    monkeypatch.setattr(
        welcome,
        "_load_players",
        lambda: [{"player_id": "abc", "player_info": {"display_name": "Fern"}}],
    )
    answers = iter(["9", "3"])  # out-of-range choice, then exit
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    result = welcome.select_player()
    assert result is None
    out, _ = capsys.readouterr()
    assert 'Hmm, I\'m not sure what you mean by "9"' in out


def test_main_verbose_flag_sets_verbose(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["idle_chapters", "-v"])
    monkeypatch.setattr(main_mod, "player_menu", lambda: None)
    main_mod.main()
    assert ui_errors.is_verbose() is True
