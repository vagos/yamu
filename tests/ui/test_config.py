from __future__ import annotations

import argparse
from types import SimpleNamespace

from yamu.ui.commands import config as config_cmd


def test_config_subparser() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    config_cmd.add_subparser(subparsers)

    args = parser.parse_args(["config"])

    assert args.command == "config"
    assert args.func is config_cmd.run


def test_config_command_prints_resolved_config(library, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        config_cmd,
        "load_config",
        lambda: {
            "library": {"path": "~/.local/share/yamu/library.db"},
            "plugins": ["steam", "howlongtobeat"],
            "howlongtobeat": {"minimum_similarity": 0.4},
        },
    )

    args = SimpleNamespace(paths=False)
    assert config_cmd.run(args, library) == 0
    output = capsys.readouterr().out
    assert "plugins:" in output
    assert "howlongtobeat:" in output


def test_config_command_prints_paths(library, monkeypatch, capsys) -> None:
    monkeypatch.setattr(config_cmd, "default_config_path", lambda: "/tmp/default.yaml")
    monkeypatch.setattr(config_cmd, "user_config_path", lambda: "/tmp/user.yaml")

    args = SimpleNamespace(paths=True)
    assert config_cmd.run(args, library) == 0
    output = capsys.readouterr().out.splitlines()
    assert output == ["/tmp/default.yaml", "/tmp/user.yaml"]
