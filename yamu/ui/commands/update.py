from __future__ import annotations

import argparse

from yamu.library.library import Library
from yamu.util.color import error, success


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("update", help="Update a game by id")
    parser.add_argument("id", type=int)
    parser.add_argument("--title")
    parser.add_argument("--platform")
    parser.add_argument("--release-date")
    parser.add_argument("--genre")
    parser.add_argument("--developer")
    parser.add_argument("--publisher")
    parser.add_argument("--region")
    parser.add_argument("--path")
    parser.add_argument("--collection")
    parser.add_argument("--status")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, library: Library) -> int:
    changes = {
        "title": args.title,
        "platform": args.platform,
        "release_date": args.release_date,
        "genre": args.genre,
        "developer": args.developer,
        "publisher": args.publisher,
        "region": args.region,
        "path": args.path,
        "collection": args.collection,
        "status": args.status,
    }
    game = library.update_game(args.id, changes)
    if not game:
        print(error(f"No game with id {args.id}"))
        return 1
    print(success(f"Updated {game.id}: {game.title}"))
    return 0
