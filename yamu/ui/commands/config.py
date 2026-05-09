from __future__ import annotations

import argparse

import yaml

from yamu.library.library import Library
from yamu.util.config import default_config_path, load_config, user_config_path


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("config", help="Show the resolved configuration")
    parser.add_argument(
        "--paths",
        action="store_true",
        help="Show the config files used to build the merged configuration",
    )
    parser.set_defaults(func=run)


def _dump_config(config: dict) -> str:
    return yaml.safe_dump(config, sort_keys=False).rstrip()


def run(args: argparse.Namespace, _library: Library) -> int:
    if args.paths:
        print(default_config_path())
        print(user_config_path())
        return 0

    config = load_config()
    print(_dump_config(config))
    return 0
