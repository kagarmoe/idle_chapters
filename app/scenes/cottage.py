import json
import textwrap
from pathlib import Path

from app.ui.text import PADDING, fill_width, print_block
from app.scenes.inventory import load_inventory, save_inventory
from app.scenes.welcome import save_player


REPO_ROOT = Path(__file__).resolve().parents[1]
TEA_FILE = REPO_ROOT / "assets" / "tea.json"


INTERACTIONS = [
    {
        "interaction_id": "cottage_wake",
        "prompt": (
            "The cottage rests in a quiet countryside, with a thatched roof, whitewashed walls, "
            "and a garden of cheerful blooms. Inside, a soft fire glows, wood furniture adds "
            "warmth, and small, familiar details make the space feel lived-in. You wake here, "
            "calm and well-rested, with time to ease into the day. Would you like to linger a "
            "little longer, or get up and look around?"
        ),
        "choices": [
            {
                "choice_id": "rest_longer",
                "label": "Rest a bit longer",
                "result": (
                    "You stay tucked into the comfort of your cottage. Light drifts through the "
                    "curtains, and the outdoors hums in a gentle hush. You breathe slowly, "
                    "enjoying the stillness, and let yourself settle back into a quiet pause."
                ),
            },
            {
                "choice_id": "look_around",
                "label": "Get up and look around",
                "result": (
                    "You rise from the bed and take in the cottage's cozy glow. Outside, the "
                    "garden brightens with color and soft birdsong. The air feels fresh and "
                    "welcoming, and you take a moment to enjoy the simple calm before choosing "
                    "what comes next."
                ),
            },
            {
                "choice_id": "make_tea",
                "label": "Make a cup of tea",
                "result": (
                    "You pad to the kitchen corner and set the kettle on. The cottage settles "
                    "around you as you choose your tea and ready a cup. When the water is warm, "
                    "you pour slowly and watch the steam rise, a gentle signal that the day can "
                    "begin at its own pace."
                ),
                "add_collectible": "tea",
            },
            {
                "choice_id": "head_to_town",
                "label": "Head to town for a snack",
                "result": "You feel a gentle peckishness and decide to head out.",
                "peckish": True,
                "end_scene": True,
            },
        ],
        "repeat": True,
    },
    {
        "interaction_id": "cottage_inside",
        "prompt": (
            "You look around the cottage. The tea kettle rests on the stove and a cozy reading "
            "nook waits by the window. Chamomile tea, black tea, and biscuits sit in the "
            "cupboard. Your journal is on the table."
        ),
        "choices": [
            {
                "choice_id": "take_in_cottage",
                "label": "Take in the cottage",
                "result": (
                    "You wander through the cottage, noticing its warm details. A small kitchen "
                    "nook holds what you need, the window seat looks inviting, and the dining "
                    "table feels ready for an unhurried morning. The space feels gentle and "
                    "kind, like a place that is happy to hold you."
                ),
                "add_collectible": "biscuits",
            },
            {
                "choice_id": "make_tea",
                "label": "Make a cup of tea",
                "add_collectible": "tea",
                "result": (
                    "You fill the kettle and set it on to warm. While it hums, you choose your tea, "
                    "set out a favorite cup, and let the morning settle around you. When the water "
                    "is ready, you pour slowly and watch the steam curl up, soft and fragrant. You "
                    "take your time with the first sip, hands wrapped around the warmth, and let "
                    "the quiet of the cottage keep you company."
                ),
            },
            {
                "choice_id": "pick_up_journal",
                "label": "Pick up your journal",
                "result": (
                    "You lift the journal from the table. Its cover is thick and soft, the kind "
                    "that warms under your hands. The pages are a gentle cream, with a faint "
                    "tooth to the paper that invites slow, steady writing. A ribbon marker rests "
                    "between the sheets, and the corners are rounded from careful use. It feels "
                    "like a quiet companion, waiting for small observations and kind reflections."
                ),
            },
            {
                "choice_id": "head_to_town",
                "label": "Head to town for a snack",
                "result": "You feel a gentle peckishness and decide to head out.",
                "peckish": True,
                "end_scene": True,
            },
        ],
        "repeat": True,
    },
]


def _ensure_journal_available(state):
    if state.get("journal_available"):
        return False
    state["journal_available"] = True
    state.setdefault("inventory", set()).add("journal")
    state["player"].setdefault("state", {}).setdefault("inventory", [])
    if "journal" not in state["player"]["state"]["inventory"]:
        state["player"]["state"]["inventory"].append("journal")
        save_player(state["player"])
    player_id = state["player"].get("player_id")
    if player_id:
        save_inventory(player_id, state["inventory"])
    return True


def _prepare_for_town(state, add_collectible):
    _ensure_journal_available(state)
    extra_items = {"bag", "water_bottle", "water", "mirror"}
    new_items = extra_items.difference(state["inventory"])
    for item_id in new_items:
        if add_collectible(state["player"], item_id):
            state["inventory"].add(item_id)
            state.setdefault("added_items", set()).add(item_id)
    print()
    print_block(
        "With the journal tucked safely away, you notice a gentle peckishness settling in. "
        "You gather your things: a bag, a water bottle, a small flask of water, and the "
        "journal. The cottage offers you a small mirror tucked into a quiet corner; you "
        "pick it up and slip it into your bag, pleased by its simple weight. With everything "
        "in place, you step toward town."
    )


def _load_tea_recipes():
    data = json.loads(TEA_FILE.read_text(encoding="utf-8"))
    return data.get("tea_recipes", [])


def _filter_recipes_by_inventory(recipes, inventory):
    available = set(inventory)
    filtered = []
    for recipe in recipes:
        ingredients = recipe.get("ingredients", [])
        base_ingredients = [
            item.get("ingredient_ref")
            for item in ingredients
            if item.get("role") == "base"
        ]
        if not base_ingredients:
            continue
        if all(ref in available for ref in base_ingredients if ref):
            filtered.append(recipe)
    return filtered


def _render_tea_recipe(recipe):
    lines = [
        f"{recipe.get('display_name', 'Tea')}",
        "",
        f"Intent: {recipe.get('intent', 'comfort')}",
        f"Target need: {recipe.get('target_need', 'Permission to rest')}",
        "",
        "Steps:",
    ]
    for step in recipe.get("steps", []):
        lines.append(f"- {step}")
    sensory = recipe.get("sensory_prompt")
    if sensory:
        lines.extend(["", sensory])
    print_block("\n".join(lines))


def _make_tea(inventory):
    recipes = _load_tea_recipes()
    recipes = _filter_recipes_by_inventory(recipes, inventory)
    if not recipes:
        print_block(
            "You warm a simple cup of tea and settle into its quiet comfort."
        )
        return
    _render_tea_recipe(recipes[0])


def _run_interaction(interaction, state, add_collectible):
    while True:
        print()
        print_block(interaction["prompt"])
        choices = []
        for choice in interaction.get("choices", []):
            choice_id = choice.get("choice_id")
            if choice_id == "pick_up_journal" and state.get(
                "journal_available"
            ):
                continue
            choices.append(choice)
        if not choices:
            return None
        for idx, choice in enumerate(choices, start=1):
            label = choice["label"]
            prefix = " " * PADDING + f"{idx}. "
            wrapped = textwrap.fill(
                label,
                width=fill_width(),
                initial_indent=prefix,
                subsequent_indent=" " * len(prefix),
            )
            print(wrapped)
        while True:
            selection = input(f"Choose an option (1-{len(choices)}): ").strip()
            if selection.isdigit():
                index = int(selection) - 1
                if 0 <= index < len(choices):
                    chosen = choices[index]
                    choice_id = chosen.get("choice_id")
                    print()
                    if chosen.get("peckish"):
                        _prepare_for_town(state, add_collectible)
                        return "leave"
                    if choice_id == "make_tea":
                        _make_tea(state.get("inventory", set()))
                    else:
                        print_block(chosen["result"])
                    item = chosen.get("add_collectible")
                    if item:
                        if add_collectible(state["player"], item):
                            state.setdefault("inventory", set()).add(item)
                            state.setdefault("added_items", set()).add(item)
                    if choice_id == "pick_up_journal":
                        _ensure_journal_available(state)
                    if chosen.get("end_scene"):
                        return "leave"
                    break
            print("Please choose a valid option.")
        if not interaction.get("repeat"):
            return None


def run_cottage(player, add_collectible):
    player_id = player.get("player_id")
    inventory = load_inventory(player_id) if player_id else set()
    if not inventory:
        inventory = set(player.get("state", {}).get("inventory", []))
    journal_available = "journal" in player.get("state", {}).get(
        "inventory", []
    )
    state = {
        "player": player,
        "inventory": inventory,
        "added_items": set(),
        "journal_available": journal_available,
    }
    for item_id in ("black_tea", "chamomile_flower"):
        if item_id not in state["inventory"]:
            if add_collectible(player, item_id):
                state["inventory"].add(item_id)
    for interaction in INTERACTIONS:
        result = _run_interaction(interaction, state, add_collectible)
        if result == "leave":
            return
