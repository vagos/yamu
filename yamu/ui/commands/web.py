from __future__ import annotations

import argparse

from yamu.library.library import Library
from yamu.util.config import load_config
from yamuplug.web import run_server


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("web", help="Browse the library in a web UI")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, library: Library) -> int:
    config = load_config()
    web_cfg = config.get("web", {})
    host = args.host or web_cfg.get("host", "127.0.0.1")
    port = args.port or int(web_cfg.get("port", 8337))
    run_server(library, host, port)
    return 0
