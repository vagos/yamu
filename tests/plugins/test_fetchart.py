from __future__ import annotations

from pathlib import Path

from yamuplug import fetchart


def test_steam_appid_from_path() -> None:
    assert fetchart._steam_appid_from_path("steam://123") == "123"
    assert fetchart._steam_appid_from_path("/games") is None
    assert fetchart._steam_appid_from_path(None) is None


def test_fetch_art_for_game(library, tmp_path, monkeypatch) -> None:
    game = library.add_game({"title": "Game A", "path": "steam://123"})

    def fake_fetch(_appid, dest: Path) -> None:
        dest.write_bytes(b"art")

    monkeypatch.setattr(fetchart, "fetch_steam_art", fake_fetch)

    config = {"fetchart": {"dir": str(tmp_path)}}
    artpath = fetchart.fetch_art_for_game(library, game.id, config)
    assert artpath is not None
    assert Path(artpath).exists()
    updated = library.get_game(game.id)
    assert updated is not None
    assert updated.artpath == artpath
