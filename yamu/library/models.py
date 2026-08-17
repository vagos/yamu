from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable

from yamu.plugins import PluginConflictError, game_field_types


GAME_FIELD_TYPES = {
    "title": "TEXT",
    "platform": "TEXT",
    "release_date": "TEXT",
    "genre": "TEXT",
    "developer": "TEXT",
    "publisher": "TEXT",
    "region": "TEXT",
    "path": "TEXT",
    "collection": "TEXT",
    "status": "TEXT",
    "artpath": "TEXT",
}

GAME_FIELDS = list(GAME_FIELD_TYPES)


def all_game_field_types() -> dict[str, str]:
    fields = dict(GAME_FIELD_TYPES)
    for name, sql_type in game_field_types().items():
        existing = fields.get(name)
        if existing is not None and existing != sql_type:
            raise PluginConflictError(
                f"Plugin field {name} conflicts with a core field type."
            )
        fields[name] = sql_type
    return fields


def all_game_fields() -> list[str]:
    return list(all_game_field_types())


@dataclass
class Game:
    id: int
    title: str
    platform: str | None = None
    release_date: str | None = None
    genre: str | None = None
    developer: str | None = None
    publisher: str | None = None
    region: str | None = None
    path: str | None = None
    collection: str | None = None
    status: str | None = None
    artpath: str | None = None

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Game":
        game = cls(
            id=row["id"],
            title=row["title"],
            platform=row.get("platform"),
            release_date=row.get("release_date"),
            genre=row.get("genre"),
            developer=row.get("developer"),
            publisher=row.get("publisher"),
            region=row.get("region"),
            path=row.get("path"),
            collection=row.get("collection"),
            status=row.get("status"),
            artpath=row.get("artpath"),
        )
        for field in all_game_fields():
            if field not in GAME_FIELDS and field in row:
                setattr(game, field, row[field])
        return game


def sanitize_fields(data: Dict[str, Any], allowed: Iterable[str]) -> Dict[str, Any]:
    allowed_set = set(allowed)
    return {key: value for key, value in data.items() if key in allowed_set}
