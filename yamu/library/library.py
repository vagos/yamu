from __future__ import annotations

from typing import Any, Dict

from yamu.dbcore.db import Database
from yamu.dbcore.query import Query, AndQuery
from yamu.library.models import Game, GAME_FIELDS, sanitize_fields


class Library:
    def __init__(self, path: str) -> None:
        self.db = Database(path)
        self._ensure_schema()

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
                artpath TEXT,
                tags TEXT,
                steam_tags TEXT
            )
            """
        )
        self._ensure_columns(
            {
                "status": "TEXT",
                "artpath": "TEXT",
                "tags": "TEXT",
                "steam_tags": "TEXT",
                "year_released": "INTEGER",
                "release_date": "TEXT",
            }
        )
        self.db.execute(
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

    def _ensure_columns(self, columns: dict[str, str]) -> None:
        rows = self.db.query("PRAGMA table_info(games)")
        existing = {row["name"] for row in rows}
        for name, col_type in columns.items():
            if name in existing:
                continue
            self.db.execute(f"ALTER TABLE games ADD COLUMN {name} {col_type}")

    def add_game(self, data: Dict[str, Any]) -> Game:
        fields = sanitize_fields(data, GAME_FIELDS)
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
        fields = sanitize_fields(changes, GAME_FIELDS)
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

    def upsert_achievements(self, game_id: int, achievements: list[dict]) -> None:
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
        with self.db.transaction():
            for row in rows:
                self.db.execute(
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

    def list_achievements(self, game_id: int) -> list[dict]:
        rows = self.db.query(
            "SELECT * FROM achievements WHERE game_id = ? ORDER BY achieved DESC, name",
            [game_id],
        )
        return [dict(row) for row in rows]

    def remove_game(self, game_id: int) -> bool:
        with self.db.transaction():
            cur = self.db.execute("DELETE FROM games WHERE id = ?", [game_id])
        return cur.rowcount > 0

    def close(self) -> None:
        self.db.close()
