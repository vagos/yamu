from __future__ import annotations

from typing import Iterable

from yamu.util.color import colordiff, colorize


def show_model_changes(
    before: dict,
    after: dict,
    fields: Iterable[str],
    header: str | None = None,
) -> bool:
    changed = False
    lines: list[str] = []
    for field in fields:
        if before.get(field) == after.get(field):
            continue
        old_val, new_val = colordiff(before.get(field), after.get(field))
        lines.append(f"{field}: {old_val} -> {new_val}")
        changed = True

    if not changed:
        return False

    if header:
        print(colorize("text_highlight", header))
    for line in lines:
        print(line)
    return True
