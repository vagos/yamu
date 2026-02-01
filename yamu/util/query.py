from __future__ import annotations

from yamu.dbcore.query import CONTAINS_FIELDS, Query, parse_query
from yamu.library.models import GAME_FIELDS


def allowed_game_fields(include_id: bool = True) -> set[str]:
    fields = set(GAME_FIELDS)
    if include_id:
        fields.add("id")
    return fields


def build_query(parts: list[str], allowed_fields: set[str]) -> Query:
    return parse_query(
        parts,
        default_field="title",
        allowed_fields=allowed_fields,
        contains_fields=CONTAINS_FIELDS,
    )


def build_game_query(
    parts: list[str],
    *,
    include_id: bool = True,
    extra_fields: set[str] | None = None,
) -> tuple[Query, set[str]]:
    allowed_fields = allowed_game_fields(include_id=include_id)
    if extra_fields:
        allowed_fields = allowed_fields | set(extra_fields)
    query = build_query(parts, allowed_fields)
    return query, allowed_fields
