from __future__ import annotations

import argparse
from types import SimpleNamespace

from yamuplug import howlongtobeat as hltb_cmd
from yamu.plugins import load_plugins


def test_hltb_subparser() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    hltb_cmd.add_subparser(subparsers)

    args = parser.parse_args(["hltb"])

    assert args.command == "hltb"
    assert args.func is hltb_cmd.run


def test_hltb_command_updates_existing_game(library, monkeypatch, capsys) -> None:
    load_plugins(["howlongtobeat"])
    game = library.add_game({"title": "Borderlands"})

    monkeypatch.setattr(
        hltb_cmd,
        "fetch_hltb_fields",
        lambda title, config: {
            "hltb_main_story": 20.55,
            "hltb_main_extra": 35.83,
            "hltb_completionist": 74.57,
        },
    )

    args = SimpleNamespace(query=[], threads=1)
    assert hltb_cmd.run(args, library) == 0

    updated = library.get_game(game.id)
    assert updated is not None
    assert updated.hltb_main_story == 20.55
    assert updated.hltb_main_extra == 35.83
    assert updated.hltb_completionist == 74.57

    output = capsys.readouterr().out
    assert "Imported HLTB data for 1 games" in output
