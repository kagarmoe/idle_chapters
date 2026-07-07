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
