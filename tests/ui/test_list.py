from __future__ import annotations

import argparse
from types import SimpleNamespace

from yamu.ui.commands import list_ as list_cmd


def test_list_subparser_accepts_ls_alias() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_cmd.add_subparser(subparsers)

    args = parser.parse_args(["ls"])

    assert args.command == "ls"
    assert args.func is list_cmd.run


def test_list_command_outputs_titles(library, capsys) -> None:
    library.add_game({"title": "Game A"})
    library.add_game({"title": "Game B"})
    args = SimpleNamespace(query=[], format=None)
    assert list_cmd.run(args, library) == 0
    output = capsys.readouterr().out
    assert "Game A" in output
    assert "Game B" in output


def test_list_command_format_unknown_field(library, capsys) -> None:
    library.add_game({"title": "Game A"})
    args = SimpleNamespace(query=[], format="$nope")
    assert list_cmd.run(args, library) == 1
    output = capsys.readouterr().out
    assert "Unknown field" in output
