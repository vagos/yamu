from __future__ import annotations

import argparse

from yamu.library.library import Library
from yamu.util.changes import show_model_changes
from yamu.util.color import error, info, success, warning
from yamu.util.prompt import input_options
from yamuplug import YamuPlugin
from yamuplug.steam import list_achievements

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
    achievements = list_achievements(library, game_id)
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
    achievements = list_achievements(library, game_id)
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


class CompletionPlugin(YamuPlugin):
    def commands(self):
        return [add_subparser]


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("completion", help="Set game completion status")
    parser.add_argument("id", type=int, nargs="?", help="Game id")
    parser.add_argument(
        "status", nargs="?", help=f"One of: {', '.join(sorted(STATUSES))}"
    )
    parser.set_defaults(func=run)


def _prompt_status(game_id: int, title: str, platform: str | None) -> str | None:
    label = f"{game_id}: {title}"
    if platform:
        label += f" ({platform})"
    print(label)
    choice = input_options(("Played", "Beaten", "Abandoned", "Skip", "Quit"))
    if choice == "p":
        return "played"
    if choice == "b":
        return "beaten"
    if choice == "a":
        return "abandoned"
    if choice == "s":
        return None
    raise KeyboardInterrupt


def run(args: argparse.Namespace, library: Library) -> int:
    if args.id is not None and args.status:
        try:
            status = normalize_status(args.status)
        except ValueError as exc:
            print(error(str(exc)))
            return 1
        game = library.set_status(args.id, status)
        if not game:
            print(error(f"No game with id {args.id}"))
            return 1
        print(success(f"Set {game.id}: {game.title} -> {game.status}"))
        return 0

    if args.id is not None:
        game = library.get_game(args.id)
        if not game:
            print(error(f"No game with id {args.id}"))
            return 1
        try:
            status = _prompt_status(game.id, game.title, game.platform)
        except KeyboardInterrupt:
            print(warning("Aborted"))
            return 1
        if not status:
            print(warning("Skipped"))
            return 0
        library.set_status(game.id, status)
        print(success(f"Set {game.id}: {game.title} -> {status}"))
        return 0

    games = library.list_games_missing_status()
    if not games:
        print(info("No games missing completion status"))
        return 0
    try:
        for game in games:
            if suggest_beaten_from_achievements(library, game.id):
                print(success(f"Set {game.id}: {game.title} -> beaten"))
                continue
            status = _prompt_status(game.id, game.title, game.platform)
            if not status:
                continue
            library.set_status(game.id, status)
            print(success(f"Set {game.id}: {game.title} -> {status}"))
    except KeyboardInterrupt:
        print(warning("Aborted"))
        return 1
    return 0
