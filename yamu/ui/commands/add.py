from __future__ import annotations

import argparse

from yamu.library.library import Library
from yamu.library.models import GAME_FIELDS
from yamu.util.color import error, success


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("add", help="Add a game to the library")
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
    if not args.title:
        from yamu.util.edit_flow import edit_items_in_editor

        template = [{field: "" for field in GAME_FIELDS}]
        edited = edit_items_in_editor(template)
        if not edited:
            return 1
        entry = edited[0]
        if not isinstance(entry, dict):
            return 1
        if not entry.get("title"):
            print(error("Title is required"))
            return 1
        game = library.add_game(entry)
        print(success(f"Added {game.id}: {game.title}"))
        return 0

    game = library.add_game(
        {
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
    )
    print(success(f"Added {game.id}: {game.title}"))
    return 0
