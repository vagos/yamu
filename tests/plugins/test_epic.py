from __future__ import annotations

from yamuplug import epic


def test_candidate_fields() -> None:
    entry = {
        "title": "Hades",
        "releaseDate": "2020-09-17T00:00:00+0000",
        "developer": "Supergiant Games",
        "publisher": "Supergiant Games",
    }
    fields = epic._candidate_fields(entry)
    assert fields["title"] == "Hades"
    assert fields["release_date"] == "2020-09-17"
    assert fields["developer"] == "Supergiant Games"
    assert fields["publisher"] == "Supergiant Games"


def test_tasks_from_list(monkeypatch) -> None:
    provider = epic.EpicImportProvider()

    def fake_run(_args, _config):
        return '[{"app_name": "HadesApp", "title": "Hades"}]'

    monkeypatch.setattr(epic, "_run_legendary", fake_run)
    tasks = list(provider.tasks({"epic": {}}))
    assert len(tasks) == 1
    task = tasks[0]
    assert task.original["title"] == "Hades"
    assert task.original["path"] == "epic://HadesApp"


def test_search_uses_app_name(monkeypatch) -> None:
    provider = epic.EpicImportProvider()

    def fake_info(_app_name, _config):
        return {"title": "Hades", "releaseDate": "2020-09-17T00:00:00+0000"}

    monkeypatch.setattr(epic, "fetch_game_info", fake_info)
    game = type("G", (), {"path": "epic://HadesApp"})()
    candidates = provider.search(game, {"epic": {}})
    assert len(candidates) == 1
    assert candidates[0].fields["title"] == "Hades"
