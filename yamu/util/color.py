from __future__ import annotations

import os
from functools import lru_cache
from typing import Any
import difflib

from yamu.util.config import load_config


COLOR_ESCAPE = "\x1b"
RESET_COLOR = f"{COLOR_ESCAPE}[39;49;00m"
CODE_BY_COLOR = {
    "normal": 0,
    "bold": 1,
    "faint": 2,
    "underline": 4,
    "inverse": 7,
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "bg_black": 40,
    "bg_red": 41,
    "bg_green": 42,
    "bg_yellow": 43,
    "bg_blue": 44,
    "bg_magenta": 45,
    "bg_cyan": 46,
    "bg_white": 47,
}


DEFAULT_COLORS = {
    "text_success": ["green"],
    "text_warning": ["yellow"],
    "text_error": ["red"],
    "text_highlight": ["bold", "white"],
    "text_highlight_minor": ["bold", "cyan"],
    "text_faint": ["faint", "white"],
    "action": ["bold", "cyan"],
    "action_default": ["bold", "green"],
    "action_description": ["faint", "white"],
    "changed": ["bold", "yellow"],
    "text_diff_added": ["green"],
    "text_diff_removed": ["red"],
}


def _enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    term = os.environ.get("TERM", "")
    if term in {"", "dumb"}:
        return False
    config = load_config()
    return bool(config.get("ui", {}).get("color", True))


@lru_cache(maxsize=1)
def _color_config() -> dict[str, str]:
    config = load_config()
    colors = dict(DEFAULT_COLORS)
    cfg_colors = config.get("ui", {}).get("colors", {})
    if isinstance(cfg_colors, dict):
        for name, value in cfg_colors.items():
            if isinstance(value, list):
                colors[name] = [str(v) for v in value]
            elif isinstance(value, str):
                colors[name] = [value]

    result: dict[str, str] = {}
    for name, sequence in colors.items():
        codes: list[str] = []
        for color_name in sequence:
            code = CODE_BY_COLOR.get(color_name)
            if code is None:
                continue
            codes.append(str(code))
        if codes:
            result[name] = ";".join(codes)
    return result


def colorize(color_name: str, text: str) -> str:
    if not _enabled():
        return text
    color_code = _color_config().get(color_name)
    if not color_code:
        return text
    return f"{COLOR_ESCAPE}[{color_code}m{text}{RESET_COLOR}"


def colordiff(a: Any, b: Any) -> tuple[str, str]:
    if not _enabled():
        return str(a), str(b)
    if not isinstance(a, str) or not isinstance(b, str):
        return (
            colorize("text_diff_removed", str(a)),
            colorize("text_diff_added", str(b)),
        )
    if a == b:
        return a, b
    matcher = difflib.SequenceMatcher(a=a, b=b)
    a_out: list[str] = []
    b_out: list[str] = []
    for op, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        a_chunk = a[a_start:a_end]
        b_chunk = b[b_start:b_end]
        if op == "equal":
            a_out.append(a_chunk)
            b_out.append(b_chunk)
        elif op == "replace":
            a_out.append(colorize("text_diff_removed", a_chunk))
            b_out.append(colorize("text_diff_added", b_chunk))
        elif op == "delete":
            a_out.append(colorize("text_diff_removed", a_chunk))
        elif op == "insert":
            b_out.append(colorize("text_diff_added", b_chunk))
    return "".join(a_out), "".join(b_out)


def info(text: str) -> str:
    return colorize("text_highlight_minor", text)


def success(text: str) -> str:
    return colorize("text_success", text)


def warning(text: str) -> str:
    return colorize("text_warning", text)


def error(text: str) -> str:
    return colorize("text_error", text)
