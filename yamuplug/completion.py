from __future__ import annotations

from yamu.util.changes import show_model_changes
from yamu.util.prompt import input_options

STATUSES = {
    "played",
    "beaten",
    "abandoned",
}


def normalize_status(value: str) -> str:
    value = value.strip().lower()
    if value not in STATUSES:
        raise ValueError(f"Invalid status: {value}")
    return value


def auto_mark_beaten_from_achievements(library, game_id: int) -> None:
    game = library.get_game(game_id)
    if not game or game.status:
        return
    achievements = library.list_achievements(game_id)
    if not achievements:
        return
    unlocked = sum(1 for entry in achievements if entry.get("achieved"))
    total = len(achievements)
    if total > 0 and unlocked == total:
        library.set_status(game_id, "beaten")


def suggest_beaten_from_achievements(library, game_id: int) -> bool:
    game = library.get_game(game_id)
    if not game or game.status:
        return False
    achievements = library.list_achievements(game_id)
    if not achievements:
        return False
    unlocked = sum(1 for entry in achievements if entry.get("achieved"))
    total = len(achievements)
    if total == 0 or unlocked != total:
        return False

    before = {"status": game.status}
    after = {"status": "beaten"}
    show_model_changes(before, after, ["status"], header=f"id {game.id} {game.title}")
    choice = input_options(("Apply", "Skip"))
    if choice == "a":
        library.set_status(game_id, "beaten")
        return True
    return False
