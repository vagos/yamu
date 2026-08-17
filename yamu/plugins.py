from __future__ import annotations


class PluginConflictError(Exception):
    pass


_GAME_FIELD_TYPES: dict[str, str] = {}


def register_game_fields(fields: dict[str, str]) -> None:
    for name, sql_type in fields.items():
        existing = _GAME_FIELD_TYPES.get(name)
        if existing is not None and existing != sql_type:
            raise PluginConflictError(
                f"Plugin field {name} has already been defined with another type."
            )
        _GAME_FIELD_TYPES[name] = sql_type


def game_field_types() -> dict[str, str]:
    return dict(_GAME_FIELD_TYPES)
