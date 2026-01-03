from __future__ import annotations

import argparse
import re
from yamu.library.library import Library
from yamu.util.color import error
from yamu.util.query import allowed_game_fields, build_query


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("list", help="List games")
    parser.add_argument("query", nargs="*", help="Query parts (field:value or terms)")
    parser.add_argument("-f", "--format", help="Format string with $fields")
    parser.set_defaults(func=run)


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _render_format(fmt: str, game: object, allowed_fields: set[str]) -> str:
    def repl(match: re.Match[str]) -> str:
        field = match.group(1)
        if field not in allowed_fields:
            raise ValueError(f"Unknown field in format: {field}")
        return _format_value(getattr(game, field))

    return re.sub(r"\$([a-zA-Z_][a-zA-Z0-9_]*)", repl, fmt)


def run(args: argparse.Namespace, library: Library) -> int:
    allowed_fields = allowed_game_fields()
    query = build_query(args.query, allowed_fields)
    games = library.list_games(query)

    fmt = args.format or "$title"
    for game in games:
        try:
            line = _render_format(fmt, game, allowed_fields)
        except ValueError as exc:
            print(error(str(exc)))
            return 1
        print(line)
    return 0
