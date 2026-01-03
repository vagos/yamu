from __future__ import annotations

from typing import Iterable

from yamu.importer.pipeline import Importer, ImportTask


class StaticProvider:
    def __init__(self, tasks: Iterable[ImportTask]):
        self._tasks = list(tasks)

    def candidates(self, task: ImportTask):
        return [type("C", (), {"fields": task.original})]

    def tasks(self, config: dict):
        return iter(self._tasks)


def test_importer_adds_new_game(library, monkeypatch) -> None:
    task = ImportTask(original={"title": "Game A", "path": "steam://1"})
    importer = Importer(library, provider=StaticProvider([task]), threads=1)

    monkeypatch.setattr(
        "yamu.importer.pipeline.input_options",
        lambda *args, **kwargs: "a",
    )

    completed, updated = importer.run([task])
    assert completed == 1
    assert updated == 0
    games = library.list_games()
    assert len(games) == 1
    assert games[0].title == "Game A"


def test_importer_updates_existing_without_prompt(library) -> None:
    game = library.add_game({"title": "Game A", "path": "steam://1"})
    task = ImportTask(
        original={"title": "Game A", "path": "steam://1", "genre": "Action"}
    )
    importer = Importer(library, provider=StaticProvider([task]), threads=1)

    completed, updated = importer.run([task])
    assert completed == 0
    assert updated == 1
    updated_game = library.get_game(game.id)
    assert updated_game is not None
    assert updated_game.genre == "Action"


def test_importer_fetch_prompts_existing_apply(library, monkeypatch) -> None:
    game = library.add_game({"title": "Game A", "path": "steam://1"})
    task = ImportTask(
        original={"title": "Game A", "path": "steam://1", "genre": "Action"}
    )
    importer = Importer(
        library,
        provider=StaticProvider([task]),
        threads=1,
        prompt_existing=True,
    )

    monkeypatch.setattr(
        "yamu.importer.pipeline.prompt_apply_changes", lambda *args, **kwargs: "a"
    )

    completed, updated = importer.run([task])
    assert completed == 0
    assert updated == 1
    updated_game = library.get_game(game.id)
    assert updated_game is not None
    assert updated_game.genre == "Action"


def test_sanitize_entry_keeps_types(library) -> None:
    importer = Importer(library, threads=1)
    entry = {"release_date": "2006", "title": "Game A", "ignored": "x"}
    cleaned = importer._sanitize_entry(entry, {"release_date", "title"})
    assert cleaned == {"release_date": "2006", "title": "Game A"}
