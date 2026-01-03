from __future__ import annotations

import argparse

from yamu.library.library import Library
from yamu.util.color import error, success


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("remove", help="Remove a game by id")
    parser.add_argument("id", type=int)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, library: Library) -> int:
    removed = library.remove_game(args.id)
    if not removed:
        print(error(f"No game with id {args.id}"))
        return 1
    print(success(f"Removed {args.id}"))
    return 0
