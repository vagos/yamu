from __future__ import annotations

import argparse
import subprocess
from typing import Any, Dict, List

from yamu.library.library import Library
from yamu.library.models import GAME_FIELDS
from yamu.util.color import error, info, success, warning
from yamu.util.prompt import input_yn
from yamu.util.edit_flow import edit_items_in_editor, diff_item, prompt_apply_changes
from yamu.util.editor import dump_yaml
from yamu.util.query import allowed_game_fields, build_query


EDIT_FIELDS = ["id"] + GAME_FIELDS


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("edit", help="Edit games in your editor")
    parser.add_argument("query", nargs="*", help="Query parts (field:value or terms)")
    parser.set_defaults(func=run)


def _select_games(args: argparse.Namespace, library: Library) -> List[Dict[str, Any]]:
    allowed_fields = allowed_game_fields()
    query = build_query(args.query, allowed_fields)
    games = library.list_games(query)
    items: List[Dict[str, Any]] = []
    for game in games:
        data = {field: getattr(game, field) for field in EDIT_FIELDS}
        items.append(data)
    return items


def _diff_item(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    fields = [field for field in EDIT_FIELDS if field != "id"]
    return diff_item(before, after, fields)


def run(args: argparse.Namespace, library: Library) -> int:
    items = _select_games(args, library)
    if not items:
        print(warning("No games matched"))
        return 1

    original_yaml = dump_yaml(items)
    while True:
        try:
            edited = edit_items_in_editor(items)
        except subprocess.CalledProcessError:
            print(error("Editor exited with an error"))
            return 1
        except ValueError as exc:
            print(error(f"Failed to parse edited file: {exc}"))
            if not input_yn("Edit again? (Y/n)", require=False):
                return 1
            continue

        edited_yaml = dump_yaml(edited)
        if edited_yaml == original_yaml:
            print(info("No changes; aborting."))
            return 0

        if len(edited) != len(items):
            print(error("Edited list length does not match original"))
            if not input_yn("Edit again? (Y/n)", require=False):
                return 1
            continue

        original_by_id = {item["id"]: item for item in items}
        changes: List[tuple[int, Dict[str, Any]]] = []
        for entry in edited:
            if "id" not in entry:
                print(error("Every entry must include an id"))
                return 1
            game_id = entry["id"]
            if game_id not in original_by_id:
                print(error(f"Unknown id in edited file: {game_id}"))
                return 1
            before = original_by_id[game_id]
            diff = _diff_item(before, entry)
            if diff:
                changes.append((game_id, diff))

        if not changes:
            print(info("No changes to apply."))
            return 0

        change_entries = []
        for game_id, diff in changes:
            before = original_by_id[game_id]
            after = dict(before)
            after.update(diff)
            change_entries.append((f"id {game_id}", before, after))
        choice = prompt_apply_changes(
            change_entries,
            [field for field in EDIT_FIELDS if field != "id"],
        )
        if choice == "n":
            return 0
        if choice == "a":
            for game_id, diff in changes:
                library.update_game(game_id, diff)
            print(success(f"Updated {len(changes)} games"))
            return 0
        if choice == "e":
            continue
        print(warning("Aborted"))
        return 1
