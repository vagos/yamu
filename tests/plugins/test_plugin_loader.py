from __future__ import annotations

import pytest

import yamuplug


def test_load_plugins_warns_for_missing_plugin(monkeypatch, capsys) -> None:
    monkeypatch.setattr(yamuplug, "_LOADED_PLUGINS", set())

    def fake_import(name: str) -> None:
        raise ModuleNotFoundError(f"No module named {name!r}", name=name)

    monkeypatch.setattr(yamuplug, "import_module", fake_import)

    yamuplug.load_plugins(["missing"])

    output = capsys.readouterr().out
    assert "Plugin not found: missing" in output
    assert yamuplug._LOADED_PLUGINS == set()


def test_load_plugins_reraises_nested_import_errors(monkeypatch) -> None:
    monkeypatch.setattr(yamuplug, "_LOADED_PLUGINS", set())

    def fake_import(_name: str) -> None:
        raise ModuleNotFoundError("No module named 'requests'", name="requests")

    monkeypatch.setattr(yamuplug, "import_module", fake_import)

    with pytest.raises(ModuleNotFoundError, match="requests"):
        yamuplug.load_plugins(["igdb"])
