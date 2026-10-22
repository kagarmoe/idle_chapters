from types import SimpleNamespace

from idle_chapters.domain.intent import match_intent, split_clauses

REPO = SimpleNamespace(actions_by_id={
    "make_tea": {"intent_signature": {"phrases": ["make tea", "cup of tea"], "keywords": ["tea"]}},
    "rest_longer": {"intent_signature": {"phrases": ["rest longer"], "keywords": ["rest", "stay"]}},
    "sit_by_the_fire": {"intent_signature": {"phrases": ["sit by the fire"], "keywords": ["sit", "fire", "rest"]}},
})
CHOICES = [
    {"action_id": "rest_longer", "label": "Rest a bit longer"},
    {"action_id": "make_tea", "label": "Make a cup of tea"},
    {"action_id": "sit_by_the_fire", "label": "Sit by the fire"},
    {"choice_id": "1", "label": "Pause and breathe"},
]


def test_a_phrase_beats_a_keyword_another_action_shares() -> None:
    # "rest" is a keyword of both; only one has the phrase.
    assert match_intent("I want to sit by the fire and rest", CHOICES, REPO) == "sit_by_the_fire"
    assert match_intent("Rest!", CHOICES, REPO) == "rest_longer"


def test_labels_and_procedural_choices_match_too() -> None:
    assert match_intent("pause and breathe", CHOICES, REPO) == "1"
    assert match_intent("fly to the moon", CHOICES, REPO) is None
    # Keywords match whole words only.
    assert match_intent("stayed", CHOICES, REPO) is None


def test_clauses_split_on_and_then_and_commas() -> None:
    assert split_clauses("Make tea, then look around and rest.") == ["make tea", "look around", "rest"]
    assert split_clauses("   ") == []
    # A known label that says "and" stays whole.
    assert split_clauses("Pause and breathe, then make tea", keep=["Pause and breathe"]) == [
        "pause and breathe", "make tea",
    ]
