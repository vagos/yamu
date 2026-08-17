from __future__ import annotations

import argparse
import os
import urllib.request
from pathlib import Path

from yamu.library.library import Library
from yamu.util.color import error, info, success
from yamu.util.config import load_config
from yamu.util.query import build_game_query
from yamuplug import YamuPlugin


class FetchArtError(RuntimeError):
    pass


def _steam_appid_from_path(path: str | None) -> str | None:
    if not path:
        return None
    if not path.startswith("steam://"):
        return None
    return path.split("steam://", 1)[1]


def _steam_art_url(appid: str) -> str:
    return f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg"


def _art_dir(config: dict) -> Path:
    raw = config.get("fetchart", {}).get("dir", "~/.local/share/yamu/art")
    return Path(os.path.expanduser(str(raw)))


def fetch_steam_art(appid: str, dest: Path) -> None:
    url = _steam_art_url(appid)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as response:
            if response.status != 200:
                raise FetchArtError(f"Steam art not found for app {appid}")
            data = response.read()
    except Exception as exc:
        raise FetchArtError(str(exc)) from exc

    dest.write_bytes(data)


def fetch_art_for_path(path: str | None, config: dict) -> str | None:
    appid = _steam_appid_from_path(path)
    if not appid:
        return None
    art_dir = _art_dir(config)
    dest = art_dir / f"steam-{appid}.jpg"
    fetch_steam_art(appid, dest)
    return str(dest)


def fetch_art_for_game(library: Library, game_id: int, config: dict) -> str | None:
    game = library.get_game(game_id)
    if not game:
        return None
    if game.artpath:
        return game.artpath

    path = fetch_art_for_path(game.path, config)
    if not path:
        return None
    library.update_game(game.id, {"artpath": path})
    return path


class FetchartPlugin(YamuPlugin):
    def commands(self):
        return [add_subparser]


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("fetchart", help="Fetch game art")
    parser.add_argument("query", nargs="*", help="Query parts (field:value or terms)")
    parser.add_argument("--threads", type=int, default=4)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, library: Library) -> int:
    config = load_config()
    query, _ = build_game_query(args.query, extra_fields={"status", "artpath"})
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
