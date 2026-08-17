from __future__ import annotations

import argparse
from typing import Any

from howlongtobeatpy import HowLongToBeat

from yamu.importer.pipeline import ImportCandidate
from yamu.library.library import Library
from yamu.util.color import error, info, success
from yamu.util.config import load_config
from yamu.util.query import build_game_query
from yamuplug import YamuPlugin


class HowLongToBeatError(RuntimeError):
    pass


_FIELD_MAP = {
    "main_story": "hltb_main_story",
    "main_extra": "hltb_main_extra",
    "completionist": "hltb_completionist",
}

def _config_section(config: dict) -> dict:
    section = config.get("howlongtobeat", {})
    return section if isinstance(section, dict) else {}


def _get_service(config: dict) -> HowLongToBeat:
    section = _config_section(config)
    minimum_similarity = float(section.get("minimum_similarity", 0.4) or 0.4)
    auto_filter_times = bool(section.get("auto_filter_times", False))
    return HowLongToBeat(minimum_similarity, auto_filter_times)


def _entry_value(entry: Any, name: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(name)
    return getattr(entry, name, None)


def _to_hours(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _candidate_fields(entry: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for source, target in _FIELD_MAP.items():
        value = _to_hours(_entry_value(entry, source))
        if value is not None:
            fields[target] = value
    return fields


def fetch_hltb_fields(title: str, config: dict) -> dict[str, Any]:
    service = _get_service(config)
    similarity_case_sensitive = bool(
        _config_section(config).get("similarity_case_sensitive", False)
    )
    try:
        results = service.search(
            str(title),
            similarity_case_sensitive=similarity_case_sensitive,
        )
    except Exception as exc:
        raise HowLongToBeatError(str(exc)) from exc
    if not results:
        return {}
    best = max(results, key=lambda entry: getattr(entry, "similarity", -1) or -1)
    return _candidate_fields(best)


class HowLongToBeatImportProvider:
    name = "howlongtobeat"

    def tasks(self, _config: dict):
        return iter(())

    def search(self, game, config: dict):
        title = getattr(game, "title", None)
        if not title:
            return []
        fields = fetch_hltb_fields(str(title), config)
        if not fields:
            return []
        return [ImportCandidate(fields=fields)]


class HowlongtobeatPlugin(YamuPlugin):
    game_types = {
        "hltb_main_story": "REAL",
        "hltb_main_extra": "REAL",
        "hltb_completionist": "REAL",
    }

    def commands(self):
        return [add_subparser]

    def import_providers(self):
        return [HowLongToBeatImportProvider()]


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
                field: getattr(game, field, None)
                for field in HLTB_FIELDS
                if getattr(game, field, None) not in (None, "")
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
            if key in HLTB_FIELDS
            and value is not None
            and getattr(game, key, None) in (None, "")
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
