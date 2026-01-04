from __future__ import annotations

from yamuplug import steam


def test_extract_genres() -> None:
    details = {"genres": [{"description": "Action"}, {"description": "RPG"}]}
    assert steam.extract_genres(details) == "Action, RPG"


def test_extract_release_date() -> None:
    details = {"release_date": {"date": "Nov 29, 2006"}}
    release_date = steam.extract_release_date(details)
    assert release_date == "2006-11-29"


def test_extract_release_date_alt_format() -> None:
    details = {"release_date": {"date": "25 Mar, 2013"}}
    release_date = steam.extract_release_date(details)
    assert release_date == "2013-03-25"


def test_steam_ids() -> None:
    assert steam._steam_ids({"steam": {"steam_ids": "123"}}) == ["123"]
    assert steam._steam_ids({"steam": {"steam_ids": ["1", "2"]}}) == ["1", "2"]


def test_tasks_return_minimal_fields(monkeypatch) -> None:
    provider = steam.SteamImportProvider()

    def fake_owned(_steam_id, _key):
        return [
            {"appid": 1, "name": "Game A"},
            {"appid": 2, "name": "Game B"},
        ]

    monkeypatch.setattr(steam, "fetch_owned_games", fake_owned)

    config = {
        "steam": {
            "api_key": "x",
            "steam_ids": ["1"],
            "fetch_details": True,
            "fetch_achievements": False,
        },
    }
    tasks = list(provider.tasks(config))
    assert len(tasks) == 2
    assert tasks[0].original["title"] == "Game A"
    assert tasks[0].original["path"] == "steam://1"


def test_search_uses_appid(monkeypatch) -> None:
    provider = steam.SteamImportProvider()

    def fake_details(_appid, **_kwargs):
        return {
            "release_date": {"date": "Nov 29, 2006"},
            "genres": [{"description": "Action"}],
        }

    def fake_achievements(_steam_id, _api_key, _appid, **_kwargs):
        return [{"name": "Achieve", "achieved": 1}]

    monkeypatch.setattr(steam, "fetch_app_details", fake_details)
    monkeypatch.setattr(steam, "fetch_game_achievements", fake_achievements)

    game = type("G", (), {"title": "Game A", "path": "steam://1"})()
    config = {
        "steam": {
            "fetch_details": True,
            "fetch_achievements": True,
            "steam_ids": ["1"],
            "api_key": "x",
        }
    }
    candidates = provider.search(game, config)
    assert len(candidates) == 1
    fields = candidates[0].fields
    assert fields["genre"] == "Action"
    assert fields["release_date"] == "2006-11-29"
    assert fields["achievements"] == [{"name": "Achieve", "achieved": 1}]
