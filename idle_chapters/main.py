import argparse

from idle_chapters.ui.errors import set_verbose
from idle_chapters.ui.text import print_block
from idle_chapters.scenes.cottage import run_cottage
from idle_chapters.scenes.inventory import load_inventory, save_inventory
from idle_chapters.scenes.welcome import player_menu, save_player, welcome

def add_collectible(player, item_id) -> bool:
    player_id = player.get("player_id")
    if not player_id:
        print("No player id found; cannot save inventory.")
        return False
    inventory = load_inventory(player_id)
    if item_id in inventory:
        return False
    inventory.add(item_id)
    save_inventory(player_id, inventory)
    player.setdefault("state", {}).setdefault("inventory", [])
    if item_id not in player["state"]["inventory"]:
        player["state"]["inventory"].append(item_id)
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="idle_chapters", description="A cozy text-based adventure."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show Z535 signal words and WHAT/MEANS/DO error detail",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    set_verbose(args.verbose)
    try:
        print_block(welcome)
        player = player_menu()
        if player is None:
            return
        run_cottage(player, add_collectible)
    except KeyboardInterrupt:
        print("\nGoodbye.")
        raise SystemExit(0)


if __name__ == "__main__":
    main()



# TODO:
# ## Milestone 6 — FastAPI v1 (portfolio-facing)

# ### 6.1 App wiring

# File: `app/main.py`

# - FastAPI app
# - dependency injection for repo + stores
