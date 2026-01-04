from __future__ import annotations

import argparse
from types import SimpleNamespace

from yamu.importer.pipeline import ImportCandidate, Importer
from yamu.library.library import Library
from yamu.util.color import error, info, success
from yamu.util.config import load_config
from yamuplug import import_providers, load_plugins


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("import", help="Import games interactively")
    parser.add_argument("--threads", type=int)
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Reprocess games already in the library",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, library: Library) -> int:
    config = load_config()
    load_plugins(config.get("plugins", []))
    providers = import_providers()
    if not providers:
        print(error("No import providers registered"))
        return 1

    enabled = config.get("plugins", [])
    if enabled:
        providers = [provider for provider in providers if provider.name in enabled]
        if not providers:
            print(error("No enabled import providers"))
            return 1
    if not enabled:
        print(
            error(
                "No import sources configured. Enable a plugin and configure its settings."
            )
        )
        return 1

    existing_paths = {game.path for game in library.list_games() if game.path}

    def task_source():
        for provider in providers:
            try:
                for task in provider.tasks(config):
                    path = task.original.get("path")
                    if args.force:
                        if not path or str(path) not in existing_paths:
                            continue
                    else:
                        if path and str(path) in existing_paths:
                            continue
                    yield task
            except Exception as exc:
                print(error(f"{provider.name} import failed: {exc}"))

    threads = args.threads
    if threads is None:
        config_threads = config.get("import", {}).get("threads")
        if isinstance(config_threads, int) and config_threads > 0:
            threads = config_threads
        else:
            threads = 2
    search_providers = [
        provider for provider in providers if hasattr(provider, "search")
    ]
    provider = CandidateProvider(search_providers, config)
    importer = Importer(
        library,
        provider=provider,
        threads=threads,
        prompt_existing=args.force,
    )
    tasks = list(task_source())
    completed, updated = importer.run(tasks)
    if updated:
        print(info(f"Updated metadata for {updated} games"))
    if completed:
        print(success(f"Imported {completed} games"))
    elif not updated:
        print(info("No new games found to import"))
    return 0


class CandidateProvider:
    def __init__(self, providers: list[object], config: dict) -> None:
        self.providers = providers
        self.config = config

    def candidates(self, task) -> list[ImportCandidate]:
        candidates = [ImportCandidate(fields=dict(task.original), source="base")]
        if not self.providers:
            return candidates
        game = SimpleNamespace(**task.original)
        for provider in self.providers:
            try:
                found = list(provider.search(game, self.config))
            except Exception as exc:
                print(error(f"{provider.name} search failed: {exc}"))
                continue
            for candidate in found:
                merged = dict(task.original)
                for key, value in candidate.fields.items():
                    if value is None or value == "":
                        continue
                    merged[key] = value
                candidates.append(
                    ImportCandidate(
                        fields=merged,
                        source=getattr(provider, "name", "search"),
                    )
                )
        return candidates
