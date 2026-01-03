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


def test_import_empty_library(library, monkeypatch, capsys) -> None:
    monkeypatch.setattr(import_cmd, "import_providers", lambda: [EmptyProvider()])
    monkeypatch.setattr(import_cmd, "load_config", lambda: {"plugins": ["empty"]})
    args = SimpleNamespace(threads=None, force=False)
    assert import_cmd.run(args, library) == 0
    output = capsys.readouterr().out
    assert "No new games found to import" in output


def test_import_single_game(library, monkeypatch, capsys) -> None:
    monkeypatch.setattr(import_cmd, "import_providers", lambda: [OneGameProvider()])
    monkeypatch.setattr(import_cmd, "load_config", lambda: {"plugins": ["one"]})
    monkeypatch.setattr(
        "yamu.importer.pipeline.input_options", lambda *args, **kwargs: "a"
    )
    args = SimpleNamespace(threads=None, force=False)
    assert import_cmd.run(args, library) == 0
    output = capsys.readouterr().out
    assert "Imported 1 games" in output
