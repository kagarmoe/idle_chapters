from idle_chapters.scenes.cottage import _run_interaction


def test_invalid_selection_uses_tone_template(monkeypatch, capsys):
    interaction = {
        "prompt": "The kettle hums softly.",
        "choices": [
            {"choice_id": "look", "label": "Look around", "result": "You look around."}
        ],
    }
    answers = iter(["5", "1"])  # one bad selection, then the valid one
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    result = _run_interaction(interaction, {"player": {}}, lambda p, i: False)
    assert result is None
    out, _ = capsys.readouterr()
    assert 'Hmm, I\'m not sure what you mean by "5"' in out
    assert "Look around" in out
    assert "Please choose a valid option" not in out


def test_words_or_a_near_miss_pick_a_choice(monkeypatch, capsys):
    interaction = {
        "prompt": "The kettle hums softly.",
        "choices": [
            {"choice_id": "rest_longer", "label": "Rest a bit longer", "result": "You rest."},
            {"choice_id": "look_around", "label": "Get up and look around", "result": "You look around."},
        ],
    }
    for typed, told in [("I'd like to get up and look around", "You look around."), ("rest a bit lnger", "You rest.")]:
        answers = iter([typed])
        monkeypatch.setattr("builtins.input", lambda _: next(answers))
        _run_interaction(interaction, {"player": {}}, lambda p, i: False)
        assert told in capsys.readouterr().out
