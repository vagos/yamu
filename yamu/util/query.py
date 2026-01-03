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
