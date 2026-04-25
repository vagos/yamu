from __future__ import annotations

from types import SimpleNamespace

from yamu.importer.pipeline import ImportTask
from yamu.ui.commands import import_ as import_cmd


class EmptyProvider:
    name = "empty"

    def tasks(self, _config):
        return iter(())


class OneGameProvider:
    name = "one"

    def tasks(self, _config):
        return iter((ImportTask(original={"title": "Game A", "path": "steam://1"}),))


class DuplicateProvider:
    name = "dup"

    def tasks(self, _config):
        return iter(
            (
                ImportTask(original={"title": "Game A", "path": "steam://1"}),
                ImportTask(original={"title": "Game A", "path": "steam://1"}),
            )
        )


class ForceUpdateProvider:
    name = "force"

    def tasks(self, _config):
        return iter(
            (
                ImportTask(
                    original={
                        "title": "Game A",
                        "path": "steam://1",
                        "genre": "Action",
                    }
                ),
                ImportTask(
                    original={
                        "title": "Game B",
                        "path": "steam://2",
                        "genre": "Adventure",
                    }
                ),
            )
        )


def test_import_empty_library(library, monkeypatch, capsys) -> None:
    monkeypatch.setattr(import_cmd, "import_providers", lambda: [EmptyProvider()])
    monkeypatch.setattr(import_cmd, "load_config", lambda: {"plugins": ["empty"]})
    args = SimpleNamespace(threads=None, force=False, query=[])
    assert import_cmd.run(args, library) == 0
    output = capsys.readouterr().out
    assert "No new games found to import" in output


def test_import_single_game(library, monkeypatch, capsys) -> None:
    monkeypatch.setattr(import_cmd, "import_providers", lambda: [OneGameProvider()])
    monkeypatch.setattr(import_cmd, "load_config", lambda: {"plugins": ["one"]})
    monkeypatch.setattr(
        "yamu.importer.pipeline.input_options", lambda *args, **kwargs: "a"
    )
    args = SimpleNamespace(threads=None, force=False, query=[])
    assert import_cmd.run(args, library) == 0
    output = capsys.readouterr().out
    assert "Imported 1 games" in output


def test_import_dedupes_paths(library, monkeypatch, capsys) -> None:
    monkeypatch.setattr(import_cmd, "import_providers", lambda: [DuplicateProvider()])
    monkeypatch.setattr(import_cmd, "load_config", lambda: {"plugins": ["dup"]})
    monkeypatch.setattr(
        "yamu.importer.pipeline.input_options", lambda *args, **kwargs: "a"
    )
    args = SimpleNamespace(threads=None, force=False, query=[])
    assert import_cmd.run(args, library) == 0
    output = capsys.readouterr().out
    assert "Imported 1 games" in output


def test_import_force_can_filter_existing_subset(library, monkeypatch, capsys) -> None:
    library.add_game({"title": "Game A", "path": "steam://1"})
    library.add_game({"title": "Game B", "path": "steam://2"})
    monkeypatch.setattr(import_cmd, "import_providers", lambda: [ForceUpdateProvider()])
    monkeypatch.setattr(import_cmd, "load_config", lambda: {"plugins": ["force"]})
    monkeypatch.setattr(import_cmd, "load_plugins", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "yamu.importer.pipeline.prompt_apply_changes", lambda *args, **kwargs: "a"
    )
    args = SimpleNamespace(threads=None, force=True, query=["title:Game A"])
    assert import_cmd.run(args, library) == 0
    output = capsys.readouterr().out
    assert "Updated metadata for 1 games" in output
    assert library.get_game_by_path("steam://1").genre == "Action"
    assert library.get_game_by_path("steam://2").genre is None


def test_import_query_requires_force(library, monkeypatch, capsys) -> None:
    monkeypatch.setattr(import_cmd, "import_providers", lambda: [EmptyProvider()])
    monkeypatch.setattr(import_cmd, "load_config", lambda: {"plugins": ["empty"]})
    args = SimpleNamespace(threads=None, force=False, query=["title:Game A"])
    assert import_cmd.run(args, library) == 1
    output = capsys.readouterr().out
    assert "QUERY is only supported with --force" in output


def test_import_skips_ignored_paths(library, monkeypatch, capsys) -> None:
    library.ignore_import_path("steam://1", "Game A")
    monkeypatch.setattr(import_cmd, "import_providers", lambda: [OneGameProvider()])
    monkeypatch.setattr(import_cmd, "load_config", lambda: {"plugins": ["one"]})
    args = SimpleNamespace(threads=None, force=False, query=[])
    assert import_cmd.run(args, library) == 0
    output = capsys.readouterr().out
    assert "No new games found to import" in output


def test_import_force_skips_ignored_existing_games(
    library, monkeypatch, capsys
) -> None:
    library.add_game({"title": "Game A", "path": "steam://1"})
    library.ignore_import_path("steam://1", "Game A")
    monkeypatch.setattr(import_cmd, "import_providers", lambda: [ForceUpdateProvider()])
    monkeypatch.setattr(import_cmd, "load_config", lambda: {"plugins": ["force"]})
    monkeypatch.setattr(import_cmd, "load_plugins", lambda *_args, **_kwargs: None)
    args = SimpleNamespace(threads=None, force=True, query=["title:Game A"])
    assert import_cmd.run(args, library) == 0
    output = capsys.readouterr().out
    assert "No new games found to import" in output
    assert library.get_game_by_path("steam://1").genre is None
