from __future__ import annotations

from typing import Sequence

from yamu.util.color import colorize


def input_options(
    options: Sequence[str],
    require: bool = False,
    prompt: str | None = None,
    fallback_prompt: str | None = None,
    default: str | None = None,
) -> str:
    letters: dict[str, str] = {}
    display_letters: list[str] = []
    capitalized: list[str] = []
    first = True

    for option in options:
        found_letter = ""
        for letter in option:
            if letter.isalpha() and letter.upper() == letter:
                found_letter = letter
                break
        if not found_letter:
            for letter in option:
                if not letter.isalpha():
                    continue
                if letter.lower() not in letters:
                    found_letter = letter
                    break
        if not found_letter:
            raise ValueError("no unambiguous lettering found")

        letters[found_letter.lower()] = option
        index = option.index(found_letter)

        if not require and (
            (default is None and first)
            or (default and found_letter.lower() == default.lower())
        ):
            show_letter = f"[{found_letter.upper()}]"
            is_default = True
        else:
            show_letter = found_letter.upper()
            is_default = False

        show_letter = colorize(
            "action_default" if is_default else "action", show_letter
        )
        descr_color = "action_default" if is_default else "action_description"
        capitalized.append(
            colorize(descr_color, option[:index])
            + show_letter
            + colorize(descr_color, option[index + 1 :])
        )
        display_letters.append(found_letter.upper())
        first = False

    if require:
        default = None
    elif default is None:
        default = display_letters[0].lower()

    if not prompt:
        prompt = (
            colorize("action", ">")
            + " "
            + ", ".join(capitalized)
            + colorize("action_description", "?")
        )
    if not fallback_prompt:
        fallback_prompt = f"Enter one of {', '.join(display_letters)}:"

    resp = input(prompt)
    while True:
        resp = resp.strip().lower()
        if default is not None and not resp:
            resp = default
        if resp:
            resp = resp[0]
            if resp in letters:
                return resp
        resp = input(fallback_prompt + " ")


def input_yn(prompt: str, require: bool = False) -> bool:
    yesno = colorize("action", ">") + colorize("action_description", " Enter Y or N:")
    sel = input_options(
        ("y", "n"), require=require, prompt=prompt, fallback_prompt=yesno
    )
    return sel == "y"


def input_options_with_numbers(
    options: Sequence[str],
    count: int,
    require: bool = False,
    prompt: str | None = None,
    fallback_prompt: str | None = None,
    default: str | None = None,
) -> str:
    letters: dict[str, str] = {}
    display_letters: list[str] = []
    capitalized: list[str] = []
    first = True

    for option in options:
        found_letter = ""
        for letter in option:
            if letter.isalpha() and letter.upper() == letter:
                found_letter = letter
                break
        if not found_letter:
            for letter in option:
                if not letter.isalpha():
                    continue
                if letter.lower() not in letters:
                    found_letter = letter
                    break
        if not found_letter:
            raise ValueError("no unambiguous lettering found")

        letters[found_letter.lower()] = option
        index = option.index(found_letter)

        if not require and (
            (default is None and first)
            or (default and found_letter.lower() == default.lower())
        ):
            show_letter = f"[{found_letter.upper()}]"
            is_default = True
        else:
            show_letter = found_letter.upper()
            is_default = False

        show_letter = colorize(
            "action_default" if is_default else "action", show_letter
        )
        descr_color = "action_default" if is_default else "action_description"
        capitalized.append(
            colorize(descr_color, option[:index])
            + show_letter
            + colorize(descr_color, option[index + 1 :])
        )
        display_letters.append(found_letter.upper())
        first = False

    if require:
        default = None
    elif default is None:
        default = display_letters[0].lower()

    number_hint = f"1-{count}"
    if not prompt:
        prompt = (
            colorize("action", ">")
            + " "
            + colorize("action_description", f"Select {number_hint} or ")
            + ", ".join(capitalized)
            + colorize("action_description", "?")
        )
    if not fallback_prompt:
        fallback_prompt = f"Enter 1-{count} or one of {', '.join(display_letters)}:"

    resp = input(prompt)
    while True:
        resp = resp.strip().lower()
        if default is not None and not resp:
            resp = default
        if resp:
            if resp.isdigit():
                index = int(resp)
                if 1 <= index <= count:
                    return resp
            resp = resp[0]
            if resp in letters:
                return resp
        resp = input(fallback_prompt + " ")
