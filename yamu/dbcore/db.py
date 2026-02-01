from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function("regexp", 2, self._regexp)

    @staticmethod
    def _regexp(value: Any, pattern: Any) -> int:
        if pattern is None:
            return 0
        if value is None:
            value = ""
        if isinstance(pattern, bytes):
            pattern = pattern.decode("utf-8", "ignore")
        if isinstance(value, bytes):
            value = value.decode("utf-8", "ignore")
        try:
            return 1 if re.search(str(pattern), str(value)) else 0
        except (re.error, TypeError):
            return 0

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, tuple(params))

    def executemany(
        self, sql: str, param_list: Iterable[Iterable[Any]]
    ) -> sqlite3.Cursor:
        return self.conn.executemany(sql, [tuple(params) for params in param_list])

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        cur = self.execute(sql, params)
        return cur.fetchall()

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self.conn.execute("BEGIN")
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
