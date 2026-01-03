from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable


GAME_FIELDS = [
    "title",
    "platform",
    "release_date",
    "genre",
    "developer",
    "publisher",
    "region",
    "path",
    "collection",
    "status",
    "artpath",
]


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
        return cls(
            id=row["id"],
            title=row["title"],
            platform=row["platform"],
            release_date=row["release_date"],
            genre=row["genre"],
            developer=row["developer"],
            publisher=row["publisher"],
            region=row["region"],
            path=row["path"],
            collection=row["collection"],
            status=row["status"],
            artpath=row["artpath"],
        )


def sanitize_fields(data: Dict[str, Any], allowed: Iterable[str]) -> Dict[str, Any]:
    allowed_set = set(allowed)
    return {key: value for key, value in data.items() if key in allowed_set}
