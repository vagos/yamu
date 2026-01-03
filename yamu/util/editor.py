from __future__ import annotations

import difflib
import os
import shlex
import subprocess
from typing import Any

import yaml


def _editor_command() -> list[str]:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    return shlex.split(editor)


def open_editor(path: str) -> None:
    cmd = _editor_command()
    subprocess.run(cmd + [path], check=True)


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def load_yaml(content: str) -> Any:
    return yaml.safe_load(content)


def load_yaml_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return load_yaml(handle.read())


def diff_yaml(before: Any, after: Any) -> str:
    before_str = dump_yaml(before)
    after_str = dump_yaml(after)
    diff = difflib.unified_diff(
        before_str.splitlines(),
        after_str.splitlines(),
        fromfile="original",
        tofile="edited",
        lineterm="",
    )
    return "\n".join(diff)
