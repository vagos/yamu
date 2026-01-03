from __future__ import annotations

import argparse

from yamu.library.library import Library
from yamu.util.color import error, info, success
from yamu.util.query import allowed_game_fields, build_query
from yamu.util.config import load_config
from yamuplug.fetchart import FetchArtError, fetch_art_for_game, fetch_art_for_path


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("fetchart", help="Fetch game art")
    parser.add_argument("query", nargs="*", help="Query parts (field:value or terms)")
    parser.add_argument("--threads", type=int, default=4)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, library: Library) -> int:
    config = load_config()
    allowed_fields = allowed_game_fields() | {"status", "artpath"}
    query = build_query(args.query, allowed_fields)
    games = library.list_games(query)

    if not games:
        print(info("No games matched"))
        return 0

    fetched = 0

    def _fetch(game):
        try:
            if game.artpath:
                return ("info", game.title, "already has art")
            if args.threads and args.threads > 1:
                path = fetch_art_for_path(game.path, config)
                return (
                    ("ok", game, path)
                    if path
                    else ("info", game.title, "no art source")
                )
            path = fetch_art_for_game(library, game.id, config)
        except FetchArtError as exc:
            return ("error", game.title, str(exc))
        if path:
            return ("ok", game.title, path)
        return ("info", game.title, "no art source")

    if args.threads and args.threads > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=args.threads) as pool:
            futures = {pool.submit(_fetch, game): game for game in games}
            for future in as_completed(futures):
                status, title, message = future.result()
                if status == "ok":
                    if hasattr(title, "id") and hasattr(title, "title"):
                        library.update_game(title.id, {"artpath": message})
                        title = title.title
                    fetched += 1
                    print(success(f"{title}: {message}"))
                elif status == "error":
                    print(error(f"{title}: {message}"))
                else:
                    print(info(f"{title}: {message}"))
    else:
        for game in games:
            status, title, message = _fetch(game)
            if status == "ok":
                fetched += 1
                print(success(f"{title}: {message}"))
            elif status == "error":
                print(error(f"{title}: {message}"))
            else:
                print(info(f"{title}: {message}"))

    print(info(f"Fetched art for {fetched} games"))
    return 0
