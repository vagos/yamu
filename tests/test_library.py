from __future__ import annotations

from pathlib import Path

from yamu.library.library import Library


def test_library_crud(tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    lib = Library(str(db_path))
    try:
        game = lib.add_game(
            {
                "title": "Garry's Mod",
                "platform": "steam",
                "igdb_rating": 82.5,
                "critic_rating": 79.0,
            }
        )
        assert game.id is not None
        assert game.title == "Garry's Mod"
        assert game.igdb_rating == 82.5
        assert game.critic_rating == 79.0

        fetched = lib.get_game(game.id)
        assert fetched is not None
        assert fetched.title == "Garry's Mod"
        assert fetched.igdb_rating == 82.5
        assert fetched.critic_rating == 79.0

        updated = lib.update_game(
            game.id,
            {"genre": "Sandbox", "igdb_rating": 85.0, "critic_rating": 81.0},
        )
        assert updated is not None
        assert updated.genre == "Sandbox"
        assert updated.igdb_rating == 85.0
        assert updated.critic_rating == 81.0

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


def test_ignore_import_paths_are_persisted(tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    lib = Library(str(db_path))
    try:
        lib.ignore_import_path("steam://1", "Game A")
        lib.ignore_import_path("steam://2")

        assert lib.list_ignored_import_paths() == {"steam://1", "steam://2"}
    finally:
        lib.close()


def test_remove_game_also_removes_achievements(tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    lib = Library(str(db_path))
    try:
        game = lib.add_game({"title": "Game A"})
        lib.upsert_achievements(
            game.id,
            [{"api_name": "ach-1", "name": "Achievement", "achieved": 1}],
        )

        assert len(lib.list_achievements(game.id)) == 1
        assert lib.remove_game(game.id) is True
        assert lib.list_achievements(game.id) == []
    finally:
        lib.close()
