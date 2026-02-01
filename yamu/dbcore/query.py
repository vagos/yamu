from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Sequence


class Query:
    def clause(self) -> tuple[str, list[str]]:
        raise NotImplementedError


CONTAINS_FIELDS = {
    "title",
    "platform",
    "genre",
    "developer",
    "publisher",
    "region",
    "path",
    "collection",
    "status",
    "release_date",
}


@dataclass
class FieldQuery(Query):
    field: str
    value: str

    def clause(self) -> tuple[str, list[str]]:
        return f"{self.field} = ?", [self.value]


@dataclass
class ContainsQuery(Query):
    field: str
    value: str

    def clause(self) -> tuple[str, list[str]]:
        return f"LOWER({self.field}) LIKE ?", [f"%{self.value.lower()}%"]


@dataclass
class RegexpQuery(Query):
    field: str
    pattern: str

    def __post_init__(self) -> None:
        re.compile(self.pattern)

    def clause(self) -> tuple[str, list[str]]:
        return f"regexp({self.field}, ?)", [self.pattern]


@dataclass
class AndQuery(Query):
    queries: Sequence[Query]

    def clause(self) -> tuple[str, list[str]]:
        if not self.queries:
            return "1", []
        clauses: list[str] = []
        params: list[str] = []
        for query in self.queries:
            clause, qparams = query.clause()
            clauses.append(f"({clause})")
            params.extend(qparams)
        return " AND ".join(clauses), params


@dataclass
class OrQuery(Query):
    queries: Sequence[Query]

    def clause(self) -> tuple[str, list[str]]:
        if not self.queries:
            return "0", []
        clauses: list[str] = []
        params: list[str] = []
        for query in self.queries:
            clause, qparams = query.clause()
            clauses.append(f"({clause})")
            params.extend(qparams)
        return " OR ".join(clauses), params


def parse_query(
    parts: Iterable[str],
    default_field: str,
    allowed_fields: set[str],
    contains_fields: set[str] | None = None,
) -> Query:
    queries: list[Query] = []
    contains = contains_fields or set()
    any_fields = sorted(allowed_fields)
    for part in parts:
        if part.startswith(":") and not part.startswith("::"):
            pattern = part[1:]
            queries.append(
                OrQuery([RegexpQuery(field, pattern) for field in any_fields])
            )
            continue
        if "::" in part:
            field, value = part.split("::", 1)
            if not field:
                queries.append(
                    OrQuery([RegexpQuery(name, value) for name in any_fields])
                )
                continue
            if field not in allowed_fields:
                raise ValueError(f"Unknown field: {field}")
            queries.append(RegexpQuery(field, value))
            continue
        if ":" in part:
            field, value = part.split(":", 1)
            if field not in allowed_fields:
                raise ValueError(f"Unknown field: {field}")
            if field in contains:
                queries.append(ContainsQuery(field, value))
            else:
                queries.append(FieldQuery(field, value))
        else:
            queries.append(ContainsQuery(default_field, part))
    return AndQuery(queries)
