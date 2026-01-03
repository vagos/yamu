from __future__ import annotations

from yamuplug import web


def test_format_release_date() -> None:
    assert web._format_release_date("Nov 29, 2006", "$year") == "2006"
    assert web._format_release_date("Nov 29, 2006", "$date") == "Nov 29, 2006"
    assert web._format_release_date(None, "$year") is None
