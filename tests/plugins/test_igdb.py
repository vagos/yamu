from __future__ import annotations

from yamuplug import igdb


def test_release_date_from_timestamp() -> None:
    assert igdb._release_date_from_timestamp(0) is None
    assert igdb._release_date_from_timestamp(1380009600) == "2013-09-24"


def test_candidate_fields() -> None:
    entry = {
        "name": "Doom",
        "first_release_date": 504921600,
        "genres": [{"name": "Action"}],
        "platforms": [{"name": "PC"}],
        "involved_companies": [
            {"developer": True, "company": {"name": "id Software"}},
            {"publisher": True, "company": {"name": "GT Interactive"}},
        ],
    }
    fields = igdb._candidate_fields(entry)
    assert fields["title"] == "Doom"
    assert fields["release_date"] == "1986-01-01"
    assert fields["genre"] == "Action"
    assert fields["platform"] == "PC"
    assert fields["developer"] == "id Software"
    assert fields["publisher"] == "GT Interactive"


def test_search_returns_candidates(monkeypatch) -> None:
    provider = igdb.IgdbImportProvider()

    def fake_fetch(_term, _config, limit=5):
        assert limit == 2
        return [
            {"name": "Doom", "first_release_date": 504921600},
            {"name": "Doom II", "first_release_date": 776908800},
        ]

    monkeypatch.setattr(igdb, "fetch_igdb_games", fake_fetch)
    config = {"igdb": {"search_limit": 2}}
    game = type("G", (), {"title": "Doom"})()
    candidates = provider.search(game, config)
    assert len(candidates) == 2
    assert candidates[0].fields["title"] == "Doom"
