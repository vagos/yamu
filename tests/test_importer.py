from __future__ import annotations

from typing import Iterable

from yamu.importer.pipeline import (
    ImportCandidate,
    Importer,
    ImportTask,
    _candidate_similarity,
    _sort_candidates,
)


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


def test_importer_force_apply_overwrites_fields(library, monkeypatch) -> None:
    game = library.add_game(
        {
            "title": "Game A",
            "path": "steam://1",
            "genre": "Puzzle",
            "critic_rating": 88.0,
        }
    )
    importer = Importer(library, threads=1, prompt_existing=True)
    candidates = [
        ImportCandidate(
            fields={
                "title": "Game A",
                "path": "steam://1",
                "genre": "Action",
                "critic_rating": 92.0,
            }
        )
    ]

    monkeypatch.setattr(
        "yamu.importer.pipeline.prompt_apply_changes", lambda *args, **kwargs: "a"
    )

    updated, should_quit = importer.prompt_existing_update(game, candidates)

    assert updated == 1
    assert should_quit is False
    updated_game = library.get_game(game.id)
    assert updated_game is not None
    assert updated_game.genre == "Action"
    assert updated_game.critic_rating == 92.0


def test_importer_force_merge_only_fills_missing_fields(library, monkeypatch) -> None:
    game = library.add_game(
        {
            "title": "Game A",
            "path": "steam://1",
            "genre": "Puzzle",
            "critic_rating": 88.0,
        }
    )
    importer = Importer(library, threads=1, prompt_existing=True)
    candidates = [
        ImportCandidate(
            fields={
                "title": "Game A",
                "path": "steam://1",
                "genre": "Action",
                "developer": "Valve",
                "critic_rating": 92.0,
                "igdb_rating": 80.0,
            }
        )
    ]

    monkeypatch.setattr(
        "yamu.importer.pipeline.prompt_apply_changes", lambda *args, **kwargs: "m"
    )

    updated, should_quit = importer.prompt_existing_update(game, candidates)

    assert updated == 1
    assert should_quit is False
    updated_game = library.get_game(game.id)
    assert updated_game is not None
    assert updated_game.genre == "Puzzle"
    assert updated_game.critic_rating == 88.0
    assert updated_game.developer == "Valve"
    assert updated_game.igdb_rating == 80.0


def test_importer_force_prompt_quit_returns_quit(library, monkeypatch) -> None:
    game = library.add_game({"title": "Game A", "path": "steam://1"})
    importer = Importer(
        library,
        threads=1,
        prompt_existing=True,
    )
    candidates = [
        ImportCandidate(fields={"title": "Game A", "path": "steam://1"}),
        ImportCandidate(fields={"title": "Game A Deluxe", "path": "steam://1"}),
    ]

    monkeypatch.setattr(
        "yamu.importer.pipeline.input_options_with_numbers",
        lambda *args, **kwargs: "q",
    )

    updated, should_quit = importer.prompt_existing_update(game, candidates)

    assert updated == 0
    assert should_quit is True


def test_sanitize_entry_keeps_types(library) -> None:
    importer = Importer(library, threads=1)
    entry = {"release_date": "2006", "title": "Game A", "ignored": "x"}
    cleaned = importer._sanitize_entry(entry, {"release_date", "title"})
    assert cleaned == {"release_date": "2006", "title": "Game A"}


def test_candidate_similarity_uses_overlapping_fields() -> None:
    similarity = _candidate_similarity(
        {"title": "Half-Life", "platform": "PC", "genre": "Shooter"},
        {"title": "Half Life", "platform": "Windows", "critic_rating": 92.0},
    )
    assert 0.4 < similarity < 1.0


def test_candidate_similarity_weights_title_more_heavily() -> None:
    base = {"title": "Half-Life", "platform": "PC", "genre": "Shooter"}
    title_match = {"title": "Half Life", "platform": "Switch", "genre": "Puzzle"}
    metadata_match = {"title": "Other Game", "platform": "PC", "genre": "Shooter"}

    assert _candidate_similarity(base, title_match) > _candidate_similarity(
        base, metadata_match
    )


def test_candidates_sorted_by_similarity() -> None:
    base = {"title": "Portal", "platform": "PC"}
    candidates = [
        ImportCandidate(fields={"title": "Other Game", "platform": "PC"}),
        ImportCandidate(fields={"title": "Portal", "platform": "PC"}),
        ImportCandidate(fields={"title": "Portal 2", "platform": "PC"}),
    ]

    sorted_candidates = _sort_candidates(base, candidates)

    assert sorted_candidates[0].fields["title"] == "Portal"


def test_prompt_shows_similarity_for_candidates(library, capsys, monkeypatch) -> None:
    importer = Importer(library, threads=1)
    task = ImportTask(original={"title": "Game A", "platform": "PC"})
    candidates = [
        ImportCandidate(fields={"title": "Game A", "platform": "PC"}),
        ImportCandidate(fields={"title": "Different", "platform": "Switch"}),
    ]
    monkeypatch.setattr(
        "yamu.importer.pipeline.input_options_with_numbers",
        lambda *args, **kwargs: "s",
    )

    action, selected = importer._prompt(task, candidates)

    assert action == "s"
    assert selected == 0
    output = capsys.readouterr().out
    assert "100.0%" in output
