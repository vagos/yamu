from __future__ import annotations

from yamuplug import web


def test_format_release_date() -> None:
    assert web._format_release_date("Nov 29, 2006", "$year") == "2006"
    assert web._format_release_date("Nov 29, 2006", "$date") == "Nov 29, 2006"
    assert web._format_release_date(None, "$year") is None


def test_resolve_static_path_blocks_traversal() -> None:
    static_root = web._asset_path("static").resolve()

    assert web._resolve_static_path("yamu.css") == static_root / "yamu.css"
    assert web._resolve_static_path("../../README.md") is None


def test_rep_includes_hltb_fields() -> None:
    game = type(
        "G",
        (),
        {
            "id": 1,
            "title": "Hades",
            "platform": "steam",
            "genre": None,
            "developer": None,
            "publisher": None,
            "region": None,
            "path": None,
            "collection": None,
            "status": None,
            "artpath": None,
            "release_date": "2020-09-17",
            "hltb_main_story": 10.5,
            "hltb_main_extra": 20.0,
            "hltb_completionist": 40.0,
        },
    )()

    rep = web._rep(game)

    assert rep["hltb_main_story"] == 10.5
    assert rep["hltb_main_extra"] == 20.0
    assert rep["hltb_completionist"] == 40.0
