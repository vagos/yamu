from __future__ import annotations

import argparse

from yamu.library.library import Library
from yamu.util.color import error, info, success
from yamu.util.config import load_config
from yamu.util.query import build_game_query
from yamuplug.howlongtobeat import HowLongToBeatError, fetch_hltb_fields


HLTB_FIELDS = {
    "hltb_main_story",
    "hltb_main_extra",
    "hltb_completionist",
}


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("hltb", help="Fetch HowLongToBeat data")
    parser.add_argument("query", nargs="*", help="Query parts (field:value or terms)")
    parser.add_argument("--threads", type=int, default=4)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, library: Library) -> int:
    config = load_config()
    query, _ = build_game_query(args.query, extra_fields=HLTB_FIELDS)
    games = library.list_games(query)

    if not games:
        print(info("No games matched"))
        return 0

    updated = 0

    def _fetch(game):
        try:
            current = {
                field: getattr(game, field)
                for field in HLTB_FIELDS
                if getattr(game, field) not in (None, "")
            }
            if len(current) == len(HLTB_FIELDS):
                return ("info", game.title, "already has hltb data")
            fields = fetch_hltb_fields(str(game.title), config)
        except HowLongToBeatError as exc:
            return ("error", game.title, str(exc))
        if not fields:
            return ("info", game.title, "no hltb source")
        updates = {
            key: value
            for key, value in fields.items()
            if key in HLTB_FIELDS and value is not None and getattr(game, key) in (None, "")
        }
        if not updates:
            return ("info", game.title, "already has hltb data")
        return ("ok", game, updates)

    if args.threads and args.threads > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=args.threads) as pool:
            futures = {pool.submit(_fetch, game): game for game in games}
            for future in as_completed(futures):
                status, title, message = future.result()
                if status == "ok":
                    if hasattr(title, "id") and hasattr(title, "title"):
                        library.update_game(title.id, message)
                        title = title.title
                    updated += 1
                    print(success(f"{title}: updated HLTB data"))
                elif status == "error":
                    print(error(f"{title}: {message}"))
                else:
                    print(info(f"{title}: {message}"))
    else:
        for game in games:
            status, title, message = _fetch(game)
            if status == "ok":
                library.update_game(title.id, message)
                updated += 1
                print(success(f"{title.title}: updated HLTB data"))
            elif status == "error":
                print(error(f"{title}: {message}"))
            else:
                print(info(f"{title}: {message}"))

    print(info(f"Imported HLTB data for {updated} games"))
    return 0
