from __future__ import annotations

import argparse

from yamu.library.library import Library
from yamu.util.config import load_config
from yamu.util.color import error, success, warning
from yamuplug.steam import (
    SteamError,
    fetch_owned_games,
    fetch_app_details,
    get_api_key,
    extract_genres,
    extract_release_date,
    _cache_paths,
    _load_cache,
    _rate_config,
    _save_cache,
)


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("steam", help="Import games from Steam")
    parser.add_argument("steam_id", help="SteamID64")
    parser.add_argument("--api-key", help="Steam Web API key (or set STEAM_API_KEY)")
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable Steam appdetails cache"
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, library: Library) -> int:
    try:
        config = load_config()
        api_key = args.api_key or get_api_key(config)
        games = fetch_owned_games(args.steam_id, api_key)
    except SteamError as exc:
        print(error(str(exc)))
        return 1
    added = 0
    fetch_details = bool(config.get("steam", {}).get("fetch_details", False))
    delay, retries, backoff, ttl = _rate_config(config)
    if args.no_cache:
        ttl = 0
    cache_path, _ = _cache_paths(config)
    cache = _load_cache(cache_path) if ttl > 0 else None
    for game in games:
        appid = game.get("appid")
        name = game.get("name")
        if not appid or not name:
            continue
        path = f"steam://{appid}"
        if library.get_game_by_path(path):
            continue
        genre = None
        release_date = None
        if fetch_details:
            details = fetch_app_details(
                str(appid),
                retries=retries,
                backoff=backoff,
                cache=cache,
                ttl=ttl,
            )
            genre = extract_genres(details)
            release_date = extract_release_date(details)
            if delay:
                import time

                time.sleep(delay)
        library.add_game(
            {
                "title": name,
                "platform": "steam",
                "path": path,
                "genre": genre,
                "release_date": release_date,
            }
        )
        added += 1
    if cache is not None:
        _save_cache(cache_path, cache)
    if added == 0:
        print(warning("No new games to import from Steam"))
    else:
        print(success(f"Imported {added} games from Steam"))
    return 0
