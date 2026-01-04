from __future__ import annotations

import argparse
from typing import Callable

from yamu.library.library import Library
from yamu.util.config import load_config
from yamu.ui.commands import (
    add,
    list_,
    update,
    remove,
    steam,
    import_,
    edit,
    completion,
    web,
    fetchart,
)
from yamuplug import load_plugins


CommandFunc = Callable[[argparse.Namespace, Library], int]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yamu", description="Game library manager")
    parser.add_argument("--db", help="Override library database path")

    config = load_config()
    load_plugins(config.get("plugins", []))
    enabled = set(config.get("plugins", []))

    subparsers = parser.add_subparsers(dest="command", required=True)
    add.add_subparser(subparsers)
    list_.add_subparser(subparsers)
    update.add_subparser(subparsers)
    remove.add_subparser(subparsers)
    import_.add_subparser(subparsers)
    edit.add_subparser(subparsers)
    if "steam" in enabled:
        steam.add_subparser(subparsers)
    if "completion" in enabled:
        completion.add_subparser(subparsers)
    if "web" in enabled:
        web.add_subparser(subparsers)
    if "fetchart" in enabled:
        fetchart.add_subparser(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = load_config()
    db_path = args.db or config["library"]["path"]
    library = Library(db_path)
    try:
        return args.func(args, library)
    finally:
        library.close()
