from __future__ import annotations

import pytest

from yamu.dbcore.query import parse_query


def test_parse_query_default_field_contains() -> None:
    query = parse_query(["Garry"], default_field="title", allowed_fields={"title"})
    clause, params = query.clause()
    assert clause == "(LOWER(title) LIKE ?)"
    assert params == ["%garry%"]


def test_parse_query_field_contains() -> None:
    query = parse_query(
        ["title:Garry"],
        default_field="title",
        allowed_fields={"title"},
        contains_fields={"title"},
    )
    clause, params = query.clause()
    assert clause == "(LOWER(title) LIKE ?)"
    assert params == ["%garry%"]


def test_parse_query_field_exact() -> None:
    query = parse_query(
        ["release_date:2006"],
        default_field="title",
        allowed_fields={"title", "release_date"},
        contains_fields={"title", "release_date"},
    )
    clause, params = query.clause()
    assert clause == "(LOWER(release_date) LIKE ?)"
    assert params == ["%2006%"]


def test_parse_query_unknown_field() -> None:
    with pytest.raises(ValueError):
        parse_query(["nope:value"], default_field="title", allowed_fields={"title"})
