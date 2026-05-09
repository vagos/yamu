from __future__ import annotations

from yamuplug import howlongtobeat


class FakeEntry:
    def __init__(
        self,
        similarity: float,
        main_story: float | None = None,
        main_extra: float | None = None,
        completionist: float | None = None,
    ) -> None:
        self.similarity = similarity
        self.main_story = main_story
        self.main_extra = main_extra
        self.completionist = completionist


class FakeService:
    def __init__(self, results):
        self.results = results
        self.calls: list[tuple[str, bool]] = []

    def search(self, title: str, similarity_case_sensitive: bool = False):
        self.calls.append((title, similarity_case_sensitive))
        return self.results


def test_candidate_fields() -> None:
    entry = FakeEntry(1.0, main_story=12.5, main_extra=30, completionist="45.5")
    fields = howlongtobeat._candidate_fields(entry)

    assert fields == {
        "hltb_main_story": 12.5,
        "hltb_main_extra": 30.0,
        "hltb_completionist": 45.5,
    }


def test_search_uses_best_match(monkeypatch) -> None:
    provider = howlongtobeat.HowLongToBeatImportProvider()
    service = FakeService(
        [
            FakeEntry(0.6, main_story=9.0),
            FakeEntry(0.9, main_story=11.5, main_extra=22.0, completionist=33.0),
        ]
    )

    monkeypatch.setattr(howlongtobeat, "_get_service", lambda _config: service)

    game = type("G", (), {"title": "Hades"})()
    candidates = provider.search(game, {"howlongtobeat": {}})

    assert service.calls == [("Hades", False)]
    assert len(candidates) == 1
    assert candidates[0].fields == {
        "hltb_main_story": 11.5,
        "hltb_main_extra": 22.0,
        "hltb_completionist": 33.0,
    }
