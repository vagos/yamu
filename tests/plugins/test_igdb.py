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
        "rating": 84.2,
        "aggregated_rating": 91.6,
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
    assert fields["igdb_rating"] == 84.2
    assert fields["critic_rating"] == 91.6


def test_search_returns_candidates(monkeypatch) -> None:
    provider = igdb.IgdbImportProvider()

    def fake_fetch(_term, _config, limit=5):
        assert limit == 2
        return [
            {"name": "Doom", "first_release_date": 504921600, "rating": 80.0},
            {"name": "Doom II", "first_release_date": 776908800},
        ]

    monkeypatch.setattr(igdb, "fetch_igdb_games", fake_fetch)
    config = {"igdb": {"search_limit": 2}}
    game = type("G", (), {"title": "Doom"})()
    candidates = provider.search(game, config)
    assert len(candidates) == 2
    assert candidates[0].fields["title"] == "Doom"
    assert candidates[0].fields["igdb_rating"] == 80.0


def test_fetch_igdb_games_escapes_search_term(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return b"[]"

    def fake_urlopen(request, timeout=30):
        assert timeout == 30
        captured["query"] = request.data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr(igdb, "get_igdb_token", lambda _config: "token")
    monkeypatch.setattr(igdb.urllib.request, "urlopen", fake_urlopen)

    assert igdb.fetch_igdb_games('Alpha"Beta', {"igdb": {"client_id": "client"}}) == []
    assert 'search "Alpha\\"Beta";' in captured["query"]
