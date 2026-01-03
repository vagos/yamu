from __future__ import annotations

import tempfile
from typing import Any, Dict, Iterable, List

from yamu.util.editor import dump_yaml, load_yaml, open_editor
from yamu.util.prompt import input_options
from yamu.util.changes import show_model_changes
from yamu.util.color import info


def load_yaml_list(content: str) -> List[Dict[str, Any]]:
    data = load_yaml(content)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError("Edited file must be a YAML list")
    items: List[Dict[str, Any]] = []
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("Each entry must be a mapping")
        items.append(entry)
    return items


def edit_items_in_editor(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp:
        tmp.write(dump_yaml(items))
        temp_path = tmp.name

    open_editor(temp_path)
    with open(temp_path, "r", encoding="utf-8") as handle:
        content = handle.read()
    return load_yaml_list(content)


def diff_item(
    before: Dict[str, Any],
    after: Dict[str, Any],
    fields: Iterable[str],
) -> Dict[str, Any]:
    diff: Dict[str, Any] = {}
    for key in fields:
        if before.get(key) != after.get(key):
            diff[key] = after.get(key)
    return diff


def prompt_apply_changes(
    changes: List[tuple[str, Dict[str, Any], Dict[str, Any]]],
    fields: Iterable[str],
) -> str:
    print(info("Changes:"))
    any_change = False
    for header, before, after in changes:
        any_change |= show_model_changes(before, after, fields, header=header)
    if not any_change:
        print(info("No changes to apply."))
        return "n"
    return input_options(("continue Editing", "Apply", "Cancel"))
