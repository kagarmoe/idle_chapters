from app.ui.text import print_block
from texts.cottage import run_cottage
from texts.inventory import load_inventory, save_inventory
from texts.welcome import player_menu, save_player, welcome

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
        save_player(player)
    return True


def main() -> None:
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
