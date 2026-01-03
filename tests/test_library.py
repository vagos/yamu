from __future__ import annotations

from pathlib import Path

from yamu.library.library import Library


def test_library_crud(tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    lib = Library(str(db_path))
    try:
        game = lib.add_game({"title": "Garry's Mod", "platform": "steam"})
        assert game.id is not None
        assert game.title == "Garry's Mod"

        fetched = lib.get_game(game.id)
        assert fetched is not None
        assert fetched.title == "Garry's Mod"

        updated = lib.update_game(game.id, {"genre": "Sandbox"})
        assert updated is not None
        assert updated.genre == "Sandbox"

        assert lib.remove_game(game.id) is True
        assert lib.get_game(game.id) is None
    finally:
        lib.close()


def test_list_missing_status(tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    lib = Library(str(db_path))
    try:
        game1 = lib.add_game({"title": "Game A"})
        game2 = lib.add_game({"title": "Game B", "status": "played"})
        missing = lib.list_games_missing_status()
        missing_ids = {game.id for game in missing}
        assert game1.id in missing_ids
        assert game2.id not in missing_ids
    finally:
        lib.close()
