from __future__ import annotations

from typing import Any, Dict

from yamu.dbcore.db import Database
from yamu.dbcore.query import Query, AndQuery
from yamu.library.models import (
    Game,
    all_game_field_types,
    all_game_fields,
    sanitize_fields,
)
from yamu import plugins


class Library:
    def __init__(self, path: str) -> None:
        self.db = Database(path)
        self._ensure_schema()
        plugins.setup_library(self)

    def _ensure_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                platform TEXT,
                year_released INTEGER,
                release_date TEXT,
                genre TEXT,
                developer TEXT,
                publisher TEXT,
                region TEXT,
                path TEXT,
                collection TEXT,
                status TEXT,
                artpath TEXT
            )
            """
        )
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS ignored_imports (
                path TEXT PRIMARY KEY,
                title TEXT
            )
            """
        )
        self._ensure_columns(all_game_field_types())

    def _ensure_columns(self, columns: dict[str, str]) -> None:
        rows = self.db.query("PRAGMA table_info(games)")
        existing = {row["name"] for row in rows}
        for name, col_type in columns.items():
            if name in existing:
                continue
            self.db.execute(f"ALTER TABLE games ADD COLUMN {name} {col_type}")

    def add_game(self, data: Dict[str, Any]) -> Game:
        self._ensure_columns(all_game_field_types())
        fields = sanitize_fields(data, all_game_fields())
        if "title" not in fields or not fields["title"]:
            raise ValueError("title is required")
        columns = ", ".join(fields.keys())
        placeholders = ", ".join(["?"] * len(fields))
        values = list(fields.values())
        with self.db.transaction():
            cur = self.db.execute(
                f"INSERT INTO games ({columns}) VALUES ({placeholders})",
                values,
            )
        game_id = cur.lastrowid
        row = self.db.query("SELECT * FROM games WHERE id = ?", [game_id])[0]
        return Game.from_row(dict(row))

    def get_game(self, game_id: int) -> Game | None:
        rows = self.db.query("SELECT * FROM games WHERE id = ?", [game_id])
        if not rows:
            return None
        return Game.from_row(dict(rows[0]))

    def get_game_by_path(self, path: str) -> Game | None:
        rows = self.db.query("SELECT * FROM games WHERE path = ? LIMIT 1", [path])
        if not rows:
            return None
        return Game.from_row(dict(rows[0]))

    def list_games(self, query: Query | None = None) -> list[Game]:
        if query is None:
            query = AndQuery([])
        clause, params = query.clause()
        rows = self.db.query(f"SELECT * FROM games WHERE {clause}", params)
        return [Game.from_row(dict(row)) for row in rows]

    def list_games_missing_status(self) -> list[Game]:
        rows = self.db.query("SELECT * FROM games WHERE status IS NULL OR status = ''")
        return [Game.from_row(dict(row)) for row in rows]

    def update_game(self, game_id: int, changes: Dict[str, Any]) -> Game | None:
        self._ensure_columns(all_game_field_types())
        fields = sanitize_fields(changes, all_game_fields())
        if not fields:
            return self.get_game(game_id)
        set_clause = ", ".join([f"{key} = ?" for key in fields.keys()])
        values = list(fields.values()) + [game_id]
        with self.db.transaction():
            self.db.execute(f"UPDATE games SET {set_clause} WHERE id = ?", values)
        return self.get_game(game_id)

    def set_status(self, game_id: int, status: str | None) -> Game | None:
        changes = {"status": status}
        return self.update_game(game_id, changes)

    def remove_game(self, game_id: int) -> bool:
        with self.db.transaction():
            plugins.remove_game(self, game_id)
            cur = self.db.execute("DELETE FROM games WHERE id = ?", [game_id])
        return cur.rowcount > 0

    def ignore_import_path(self, path: str, title: str | None = None) -> None:
        with self.db.transaction():
            self.db.execute(
                """
                INSERT INTO ignored_imports (path, title)
                VALUES (?, ?)
                ON CONFLICT(path) DO UPDATE SET title = excluded.title
                """,
                [path, title],
            )

    def list_ignored_import_paths(self) -> set[str]:
        rows = self.db.query("SELECT path FROM ignored_imports")
        return {str(row["path"]) for row in rows if row["path"]}

    def close(self) -> None:
        self.db.close()
