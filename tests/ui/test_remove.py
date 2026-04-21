from __future__ import annotations

import argparse

from yamu.ui.commands import remove as remove_cmd


def test_remove_subparser_accepts_rm_alias() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    remove_cmd.add_subparser(subparsers)

    args = parser.parse_args(["rm", "123"])

    assert args.command == "rm"
    assert args.func is remove_cmd.run
