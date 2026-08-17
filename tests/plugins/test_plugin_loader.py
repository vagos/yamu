from __future__ import annotations

import pytest

import yamu.plugins as plugin_registry


def test_load_plugins_warns_for_missing_plugin(monkeypatch, capsys) -> None:
    monkeypatch.setattr(plugin_registry, "_instances", [])

    def fake_import(name: str) -> None:
        raise ModuleNotFoundError(f"No module named {name!r}", name=name)

    monkeypatch.setattr(plugin_registry, "import_module", fake_import)

    plugin_registry.load_plugins(["missing"])

    output = capsys.readouterr().out
    assert "Plugin not found: missing" in output
    assert list(plugin_registry.find_plugins()) == []


def test_load_plugins_reraises_nested_import_errors(monkeypatch) -> None:
    monkeypatch.setattr(plugin_registry, "_instances", [])

    def fake_import(_name: str) -> None:
        raise ModuleNotFoundError("No module named 'requests'", name="requests")

    monkeypatch.setattr(plugin_registry, "import_module", fake_import)

    with pytest.raises(ModuleNotFoundError, match="requests"):
        plugin_registry.load_plugins(["igdb"])
