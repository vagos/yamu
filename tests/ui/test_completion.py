from __future__ import annotations

from types import SimpleNamespace

from yamu.ui.commands import completionist


def test_completion_sets_status(library, capsys) -> None:
    game = library.add_game({"title": "Game A"})
    args = SimpleNamespace(id=game.id, status="played")
    assert completionist.run(args, library) == 0
    updated = library.get_game(game.id)
    assert updated is not None
    assert updated.status == "played"
    output = capsys.readouterr().out
    assert "Set" in output
