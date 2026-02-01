from __future__ import annotations

import argparse

from yamu.library.library import Library
from yamu.util.color import error, success, warning
from yamu.util.query import build_game_query


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("remove", help="Remove games from the library")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print matches without removing anything",
    )
    parser.add_argument(
        "query",
        nargs="+",
        help="Query parts (field:value or terms) or an id",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, library: Library) -> int:
    if len(args.query) == 1 and args.query[0].isdigit():
        game_id = int(args.query[0])
        if args.raw:
            game = library.get_game(game_id)
            if not game:
                print(error(f"No game with id {game_id}"))
                return 1
            print(f"{game.id}: {game.title}")
            return 0
        removed = library.remove_game(game_id)
        if not removed:
            print(error(f"No game with id {game_id}"))
            return 1
        print(success(f"Removed {game_id}"))
        return 0

    query, _ = build_game_query(args.query)
    games = library.list_games(query)
    if not games:
        print(warning("No games matched"))
        return 1

    if args.raw:
        for game in games:
            print(f"{game.id}: {game.title}")
        return 0

    removed = 0
    for game in games:
        if library.remove_game(game.id):
            removed += 1

    if removed == 1 and len(games) == 1:
        game = games[0]
        print(success(f"Removed {game.id}: {game.title}"))
        return 0

    print(success(f"Removed {removed} games"))
    return 0
