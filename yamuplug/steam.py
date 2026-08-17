from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
import sqlite3
from typing import Any, Dict, Iterable, List

from yamu.importer.pipeline import ImportCandidate, ImportTask
from yamu.library.library import Library
from yamu.util.color import error, success, warning
from yamu.util.config import load_config
from yamuplug import YamuPlugin


STEAM_OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
STEAM_PLAYER_ACHIEVEMENTS_URL = (
    "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
)
STEAM_SCHEMA_URL = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
STEAM_STORE_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"


class SteamError(RuntimeError):
    pass


def _get_api_key(config: dict | None = None) -> str:
    if "STEAM_API_KEY" in os.environ:
        return os.environ["STEAM_API_KEY"].strip()
    if config:
        return str(config.get("steam", {}).get("api_key", "")).strip()
    return ""


def get_api_key(config: dict | None = None) -> str:
    return _get_api_key(config)


def fetch_owned_games(steam_id: str, api_key: str) -> List[dict]:
    if not api_key:
        raise SteamError("STEAM_API_KEY is required to fetch Steam libraries")

    params = {
        "key": api_key,
        "steamid": steam_id,
        "include_appinfo": 1,
        "include_played_free_games": 1,
    }
    url = f"{STEAM_OWNED_GAMES_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    games = payload.get("response", {}).get("games", [])
    if not isinstance(games, list):
        raise SteamError("Unexpected Steam API response")
    return games


def _cache_path(config: dict, key: str, default_name: str) -> str:
    raw = str(config.get("steam", {}).get(key, "")).strip()
    if raw:
        return os.path.expanduser(raw)
    base = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    return os.path.join(base, "yamu", default_name)


def _cache_paths(config: dict) -> tuple[str, str]:
    raw = str(config.get("steam", {}).get("cache_path", "")).strip()
    if raw:
        expanded = os.path.expanduser(raw)
        if expanded.endswith(os.sep):
            details = os.path.join(expanded, "steam_appdetails.json")
            achievements = os.path.join(expanded, "steam_achievement_schema.json")
            return details, achievements
        root, ext = os.path.splitext(expanded)
        if ext:
            return f"{root}-details{ext}", f"{root}-achievements{ext}"
        return f"{expanded}-details.json", f"{expanded}-achievements.json"
    return (
        _cache_path(config, "details_cache_path", "steam_appdetails.json"),
        _cache_path(config, "achievements_cache_path", "steam_achievement_schema.json"),
    )


def _rate_config(config: dict) -> tuple[float, int, float, int]:
    delay = float(config.get("steam", {}).get("delay", 0) or 0)
    retries = int(config.get("steam", {}).get("retries", 3) or 0)
    backoff = float(config.get("steam", {}).get("backoff", 1.0) or 0)
    ttl = int(config.get("steam", {}).get("cache_ttl", 0) or 0)
    return delay, retries, backoff, ttl


def _load_cache(path: str) -> Dict[str, Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        items = payload.get("items", {})
        if isinstance(items, dict):
            return items
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return {}


def _save_cache(path: str, items: Dict[str, Dict[str, Any]]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"items": items}, handle)
    except OSError:
        return


def fetch_app_details(
    appid: str,
    retries: int = 3,
    backoff: float = 1.0,
    cache: Dict[str, Dict[str, Any]] | None = None,
    ttl: int = 0,
) -> dict:
    now = int(time.time())
    if cache is not None and ttl > 0:
        cached = cache.get(appid)
        if cached and now - int(cached.get("ts", 0)) < ttl:
            data = cached.get("data")
            if isinstance(data, dict):
                return data
    params = {"appids": appid, "l": "english"}
    url = f"{STEAM_APPDETAILS_URL}?{urllib.parse.urlencode(params)}"
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            details = payload.get(str(appid), {})
            if not details or not details.get("success"):
                return {}
            data = details.get("data", {}) or {}
            if cache is not None and ttl > 0:
                cache[appid] = {"ts": now, "data": data}
            return data
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                time.sleep(backoff * (2**attempt))
                attempt += 1
                continue
            return {}
        except Exception:
            return {}


def extract_genres(details: dict) -> str | None:
    genres = details.get("genres", []) or []
    if not isinstance(genres, list):
        return None
    values = []
    for entry in genres:
        if not isinstance(entry, dict):
            continue
        desc = entry.get("description")
        if desc:
            values.append(str(desc))
    if not values:
        return None
    return ", ".join(values)


def _normalize_release_date(value: str) -> str | None:
    raw = value.strip()
    if not raw:
        return None
    lowered = raw.lower()
    if lowered in {"coming soon", "tba", "to be announced"}:
        return raw
    replacements = {
        "Sept": "Sep",
        "sept": "sep",
    }
    for key, replacement in replacements.items():
        raw = raw.replace(key, replacement)
    formats = [
        "%b %d, %Y",
        "%d %b, %Y",
        "%b %d %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%d %B, %Y",
        "%B %d %Y",
        "%d %B %Y",
        "%b %Y",
        "%B %Y",
        "%Y",
    ]
    for fmt in formats:
        try:
            parsed = time.strptime(raw, fmt)
        except ValueError:
            continue
        if fmt in {"%Y"}:
            return f"{parsed.tm_year:04d}"
        if fmt in {"%b %Y", "%B %Y"}:
            return f"{parsed.tm_year:04d}-{parsed.tm_mon:02d}"
        return f"{parsed.tm_year:04d}-{parsed.tm_mon:02d}-{parsed.tm_mday:02d}"
    return value


def extract_release_date(details: dict) -> str | None:
    release = details.get("release_date", {})
    if not isinstance(release, dict):
        return None
    date = release.get("date")
    if not date:
        return None
    normalized = _normalize_release_date(str(date))
    return normalized


def fetch_player_achievements(
    steam_id: str,
    api_key: str,
    appid: str,
    retries: int = 3,
    backoff: float = 1.0,
) -> list[dict]:
    params = {
        "key": api_key,
        "steamid": steam_id,
        "appid": appid,
        "l": "english",
    }
    url = f"{STEAM_PLAYER_ACHIEVEMENTS_URL}?{urllib.parse.urlencode(params)}"
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            stats = payload.get("playerstats", {}) or {}
            return stats.get("achievements", []) or []
        except urllib.error.HTTPError as exc:
            if exc.code in {400, 403, 404}:
                return []
            if exc.code == 429 and attempt < retries:
                time.sleep(backoff * (2**attempt))
                attempt += 1
                continue
            raise
        except Exception:
            return []


def fetch_schema(
    api_key: str,
    appid: str,
    retries: int = 3,
    backoff: float = 1.0,
    cache: Dict[str, Dict[str, Any]] | None = None,
    ttl: int = 0,
) -> dict:
    now = int(time.time())
    if cache is not None and ttl > 0:
        cached = cache.get(appid)
        if cached and now - int(cached.get("ts", 0)) < ttl:
            data = cached.get("data")
            if isinstance(data, dict):
                return data
    params = {
        "key": api_key,
        "appid": appid,
        "l": "english",
    }
    url = f"{STEAM_SCHEMA_URL}?{urllib.parse.urlencode(params)}"
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            data = payload.get("game", {}) or {}
            if cache is not None and ttl > 0:
                cache[appid] = {"ts": now, "data": data}
            return data
        except urllib.error.HTTPError as exc:
            if exc.code in {400, 403, 404}:
                return {}
            if exc.code == 429 and attempt < retries:
                time.sleep(backoff * (2**attempt))
                attempt += 1
                continue
            raise
        except Exception:
            return {}


def _schema_map(schema: dict) -> dict[str, dict]:
    available = schema.get("availableGameStats", {}) or {}
    achievements = available.get("achievements", []) or []
    mapping: dict[str, dict] = {}
    for entry in achievements:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if name:
            mapping[str(name)] = entry
    return mapping


def fetch_store_search(term: str, limit: int = 5) -> list[dict]:
    params = {
        "term": term,
        "l": "english",
        "cc": "us",
        "category1": "998",
        "count": max(1, limit),
    }
    url = f"{STEAM_STORE_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        items = payload.get("items", []) or []
        if isinstance(items, list):
            return items
    except Exception:
        return []
    return []


def fetch_game_achievements(
    steam_id: str,
    api_key: str,
    appid: str,
    retries: int = 3,
    backoff: float = 1.0,
    cache: Dict[str, Dict[str, Any]] | None = None,
    ttl: int = 0,
) -> list[dict]:
    schema = fetch_schema(
        api_key, appid, retries=retries, backoff=backoff, cache=cache, ttl=ttl
    )
    schema_map = _schema_map(schema)
    achievements = fetch_player_achievements(
        steam_id, api_key, appid, retries=retries, backoff=backoff
    )
    normalized = []
    for entry in achievements:
        api_name = entry.get("apiname")
        if not api_name:
            continue
        schema_entry = schema_map.get(str(api_name), {})
        normalized.append(
            {
                "api_name": str(api_name),
                "name": schema_entry.get("displayName"),
                "description": schema_entry.get("description"),
                "icon": schema_entry.get("icon"),
                "icon_gray": schema_entry.get("icongray"),
                "achieved": int(entry.get("achieved", 0)),
                "unlock_time": int(entry.get("unlocktime", 0)),
            }
        )
    return normalized


def _steam_appid_from_path(path: str | None) -> str | None:
    if not path:
        return None
    if not path.startswith("steam://"):
        return None
    return path.split("steam://", 1)[1]


def import_achievements(
    library,
    steam_id: str,
    api_key: str,
    games: Iterable,
    config: dict,
) -> list[int]:
    delay, retries, backoff, ttl = _rate_config(config)
    _, cache_path = _cache_paths(config)
    cache = _load_cache(cache_path) if ttl > 0 else None

    updated_ids: list[int] = []
    for game in games:
        appid = _steam_appid_from_path(game.path)
        if not appid:
            continue
        normalized = fetch_game_achievements(
            steam_id,
            api_key,
            appid,
            retries=retries,
            backoff=backoff,
            cache=cache,
            ttl=ttl,
        )
        if normalized:
            upsert_achievements(library, game.id, normalized)
        updated_ids.append(game.id)
        if delay:
            time.sleep(delay)

    if cache is not None:
        _save_cache(cache_path, cache)
    return updated_ids


def _steam_ids(config: dict) -> list[str]:
    raw = config.get("steam", {}).get("steam_ids", [])
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if item]
    return []


class SteamImportProvider:
    name = "steam"

    def tasks(self, config: dict):
        api_key = _get_api_key(config)
        for steam_id in _steam_ids(config):
            games = fetch_owned_games(steam_id, api_key)
            for game in games:
                appid = game.get("appid")
                name = game.get("name")
                if not appid or not name:
                    continue
                path = f"steam://{appid}"
                yield ImportTask(
                    original={
                        "title": name,
                        "platform": "steam",
                        "path": path,
                    }
                )

    def search(self, game, config: dict):
        fetch_details = bool(config.get("steam", {}).get("fetch_details", False))
        fetch_achievements = bool(
            config.get("steam", {}).get("fetch_achievements", True)
        )
        api_key = _get_api_key(config)
        steam_ids = _steam_ids(config)
        delay, retries, backoff, ttl = _rate_config(config)
        cache_path, ach_cache_path = _cache_paths(config)
        cache = _load_cache(cache_path) if ttl > 0 else None
        ach_cache = _load_cache(ach_cache_path) if ttl > 0 else None
        search_limit = int(config.get("steam", {}).get("search_limit", 5) or 5)
        steam_id = steam_ids[0] if steam_ids else ""
        appids: list[str] = []
        appid = _steam_appid_from_path(getattr(game, "path", None))
        if appid:
            appids.append(appid)
        elif getattr(game, "title", None):
            results = fetch_store_search(str(game.title), limit=search_limit)
            for result in results:
                found = result.get("id")
                if found:
                    appids.append(str(found))

        candidates: list[ImportCandidate] = []
        for appid in appids:
            fields: dict[str, Any] = {}
            if fetch_details:
                details = fetch_app_details(
                    str(appid),
                    retries=retries,
                    backoff=backoff,
                    cache=cache,
                    ttl=ttl,
                )
                fields["genre"] = extract_genres(details)
                fields["release_date"] = extract_release_date(details)
                if delay:
                    time.sleep(delay)
            if fetch_achievements and api_key and steam_id:
                fields["achievements"] = fetch_game_achievements(
                    steam_id,
                    api_key,
                    str(appid),
                    retries=retries,
                    backoff=backoff,
                    cache=ach_cache,
                    ttl=ttl,
                )
                if delay:
                    time.sleep(delay)
            if fields:
                candidates.append(ImportCandidate(fields=fields))

        if cache is not None:
            _save_cache(cache_path, cache)
        if ach_cache is not None:
            _save_cache(ach_cache_path, ach_cache)
        return candidates


def ensure_achievement_schema(library) -> None:
    library.db.execute(
        """
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            api_name TEXT NOT NULL,
            name TEXT,
            description TEXT,
            icon TEXT,
            icon_gray TEXT,
            achieved INTEGER,
            unlock_time INTEGER,
            UNIQUE(game_id, api_name)
        )
        """
    )


def upsert_achievements(library, game_id: int, achievements: list[dict]) -> None:
    ensure_achievement_schema(library)
    rows = []
    for entry in achievements:
        rows.append(
            (
                game_id,
                entry.get("api_name"),
                entry.get("name"),
                entry.get("description"),
                entry.get("icon"),
                entry.get("icon_gray"),
                entry.get("achieved", 0),
                entry.get("unlock_time", 0),
            )
        )
    with library.db.transaction():
        for row in rows:
            library.db.execute(
                """
                INSERT INTO achievements
                    (game_id, api_name, name, description, icon, icon_gray, achieved, unlock_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id, api_name)
                DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    icon=excluded.icon,
                    icon_gray=excluded.icon_gray,
                    achieved=excluded.achieved,
                    unlock_time=excluded.unlock_time
                """,
                row,
            )


def list_achievements(library, game_id: int) -> list[dict]:
    try:
        rows = library.db.query(
            "SELECT * FROM achievements WHERE game_id = ? ORDER BY achieved DESC, name",
            [game_id],
        )
    except sqlite3.OperationalError:
        return []
    return [dict(row) for row in rows]


class SteamPlugin(YamuPlugin):
    def commands(self):
        return [add_subparser]

    def import_providers(self):
        return [SteamImportProvider()]

    def setup_library(self, library) -> None:
        ensure_achievement_schema(library)

    def handle_import_fields(self, library, game_id: int, fields: dict[str, Any]) -> None:
        achievements = fields.get("achievements")
        if achievements:
            upsert_achievements(library, game_id, achievements)

    def remove_game(self, library, game_id: int) -> None:
        try:
            library.db.execute("DELETE FROM achievements WHERE game_id = ?", [game_id])
        except sqlite3.OperationalError:
            return


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
