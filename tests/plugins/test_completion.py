from __future__ import annotations

from yamuplug import completion
from yamuplug.steam import upsert_achievements


def test_normalize_status() -> None:
    assert completion.normalize_status("Played") == "played"


def test_suggest_beaten_from_achievements(library, monkeypatch) -> None:
    game = library.add_game({"title": "Game A"})
    upsert_achievements(
        library,
        game.id,
        [
            {"api_name": "a", "name": "A", "achieved": 1},
            {"api_name": "b", "name": "B", "achieved": 1},
        ],
    )
    monkeypatch.setattr(
        "yamuplug.completion.input_options", lambda *args, **kwargs: "a"
    )
    assert completion.suggest_beaten_from_achievements(library, game.id) is True
    updated = library.get_game(game.id)
    assert updated is not None
    assert updated.status == "beaten"


def test_auto_mark_beaten_from_achievements(library) -> None:
    game = library.add_game({"title": "Game A"})
    upsert_achievements(
        library,
        game.id,
        [
            {"api_name": "a", "name": "A", "achieved": 1},
            {"api_name": "b", "name": "B", "achieved": 1},
        ],
    )
    completion.auto_mark_beaten_from_achievements(library, game.id)
    updated = library.get_game(game.id)
    assert updated is not None
    assert updated.status == "beaten"
