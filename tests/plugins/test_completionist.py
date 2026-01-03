from __future__ import annotations

from yamuplug import completionist


def test_normalize_status() -> None:
    assert completionist.normalize_status("Played") == "played"


def test_suggest_beaten_from_achievements(library, monkeypatch) -> None:
    game = library.add_game({"title": "Game A"})
    library.upsert_achievements(
        game.id,
        [
            {"api_name": "a", "name": "A", "achieved": 1},
            {"api_name": "b", "name": "B", "achieved": 1},
        ],
    )
    monkeypatch.setattr(
        "yamuplug.completionist.input_options", lambda *args, **kwargs: "a"
    )
    assert completionist.suggest_beaten_from_achievements(library, game.id) is True
    updated = library.get_game(game.id)
    assert updated is not None
    assert updated.status == "beaten"


def test_auto_mark_beaten_from_achievements(library) -> None:
    game = library.add_game({"title": "Game A"})
    library.upsert_achievements(
        game.id,
        [
            {"api_name": "a", "name": "A", "achieved": 1},
            {"api_name": "b", "name": "B", "achieved": 1},
        ],
    )
    completionist.auto_mark_beaten_from_achievements(library, game.id)
    updated = library.get_game(game.id)
    assert updated is not None
    assert updated.status == "beaten"
