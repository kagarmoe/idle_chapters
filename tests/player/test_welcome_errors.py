from idle_chapters.scenes import welcome


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
