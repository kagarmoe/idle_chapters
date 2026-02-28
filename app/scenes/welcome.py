welcome = """
Welcome to Idle Chapters!
This is a cozy text-based adventure game where your choices shape the story.
Enjoy your journey!
"""

import json
import os
import uuid
from pathlib import Path

from jsonschema import SchemaError, ValidationError

from app.content.loader import load_json
from app.content.schema_utils import load_validator
PLAYER_FILE = "assets/player.json"
PLAYERS_FILE = "assets/players.json"
PLAYER_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "players.schema.json"


def save_player(player_data):
    """Saves the player dictionary to a JSON file."""
    try:
        with open(PLAYER_FILE, "w", encoding="utf-8") as f:
            json.dump(player_data, f, indent=4)
        display_name = player_data.get("player_info", {}).get("display_name") or "friend"
        print(f"\nPlayer {display_name} saved to {PLAYER_FILE}")
    except IOError as e:
        print(f"Error saving file: {e}")


def _save_players(players):
    try:
        with open(PLAYERS_FILE, "w", encoding="utf-8") as f:
            json.dump(players, f, indent=4)
    except IOError as e:
        print(f"Error saving file: {e}")


def load_player():
    """Loads player data from a JSON file, if it exists."""
    if os.path.exists(PLAYER_FILE):
        try:
            data = load_json(PLAYER_FILE, schema_path=PLAYER_SCHEMA)
            if not _validate_player(data):
                print("Existing player data is invalid. Creating a new player.")
                return {}
            if _ensure_player_id(data):
                save_player(data)
            return data
        except (ValueError, FileNotFoundError):
            print("Error loading player file. Creating a new player.")
            return {}
    return {}


def _load_players():
    if os.path.exists(PLAYERS_FILE):
        try:
            data = load_json(PLAYERS_FILE)
            if not isinstance(data, list):
                print("Existing players data is invalid. Creating a new list.")
                return []
            valid_players = []
            for entry in data:
                if isinstance(entry, dict) and _validate_player(entry):
                    valid_players.append(entry)
            return valid_players
        except (ValueError, FileNotFoundError):
            print("Error loading players file. Creating a new list.")
            return []
    return []


def _select_pronouns():
    options = {
        "1": ("she_her", "she", "her", "hers"),
        "2": ("he_him", "he", "him", "his"),
        "3": ("they_them", "they", "them", "theirs"),
        "4": ("ze_hir", "ze", "hir", "hirs"),
        "5": ("you_your", "you", "you", "yours"),
    }

    while True:
        print("1. 'she', 'her', 'hers'")
        print("2. 'he', 'him', 'his'")
        print("3. 'they', 'them', 'theirs'")
        print("4. 'ze', 'zir', 'zirs'")
        print("5. 'you', 'your', 'yours' (for a 2nd person experience)")
        print("6. Exit game")

        choice = input("Choose your pronouns (1-6): ").strip()
        if choice == "6":
            return None
        if choice in options:
            pronoun_key, subject, obj, possessive = options[choice]
            return {
                "key": pronoun_key,
                "subject": subject,
                "object": obj,
                "possessive": possessive,
            }
        print("Please choose a valid option (1-6).")


def _ensure_player_id(player: dict) -> bool:
    if player.get("player_id"):
        return False
    player["player_id"] = uuid.uuid4().hex
    return True


def _validate_player(player: dict) -> bool:
    try:
        validator = load_validator(PLAYER_SCHEMA)
        validator.validate(instance=player)
    except (ValidationError, SchemaError) as exc:
        print(f"Player data failed schema validation: {exc.message}")
        return False
    return True


def player_menu():
    """Player selects an existing profile or creates a new one."""
    player = select_player()
    if player is None:
        return None
    display_name = player.get("player_info", {}).get("display_name") or "friend"
    print(f"\nHello, {display_name}! Let's begin your adventure.\n")
    return player


def select_player():
    players = _load_players()
    updated_players = False
    for entry in players:
        if _ensure_player_id(entry):
            updated_players = True
    if updated_players:
        _save_players(players)
    if not players:
        print("No previous players found. Creating a new player.")
        player = _create_player()
        if player is None:
            return None
        players.append(player)
        _save_players(players)
        save_player(player)
        return player

    while True:
        print("Select a player:")
        for idx, player in enumerate(players, start=1):
            display_name = player.get("player_info", {}).get("display_name") or "friend"
            print(f"{idx}. {display_name}")
        print(f"{len(players) + 1}. Create a new player")
        print(f"{len(players) + 2}. Exit game")

        choice = input(f"Choose a player (1-{len(players) + 2}): ").strip()
        if choice == str(len(players) + 2):
            return None
        if choice == str(len(players) + 1):
            player = _create_player()
            if player is None:
                return None
            players.append(player)
            _save_players(players)
            save_player(player)
            return player
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(players):
                player = players[index]
                save_player(player)
                return player
        print("Please choose a valid option.")


def _create_player():
    name = input("What name would you like to go by, friend? ").strip()
    pronouns = _select_pronouns()
    if pronouns is None:
        return None
    player = {
        "player_id": uuid.uuid4().hex,
        "player_info": {
            "display_name": name or None,
            "pronouns": pronouns["key"],
        }
    }
    if not _validate_player(player):
        return None
    return player
