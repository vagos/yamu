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
