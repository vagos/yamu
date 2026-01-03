from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from yamu.library.library import Library


class FetchArtError(RuntimeError):
    pass


def _steam_appid_from_path(path: str | None) -> str | None:
    if not path:
        return None
    if not path.startswith("steam://"):
        return None
    return path.split("steam://", 1)[1]


def _steam_art_url(appid: str) -> str:
    return f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg"


def _art_dir(config: dict) -> Path:
    raw = config.get("fetchart", {}).get("dir", "~/.local/share/yamu/art")
    return Path(os.path.expanduser(str(raw)))


def fetch_steam_art(appid: str, dest: Path) -> None:
    url = _steam_art_url(appid)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as response:
            if response.status != 200:
                raise FetchArtError(f"Steam art not found for app {appid}")
            data = response.read()
    except Exception as exc:
        raise FetchArtError(str(exc)) from exc

    dest.write_bytes(data)


def fetch_art_for_path(path: str | None, config: dict) -> str | None:
    appid = _steam_appid_from_path(path)
    if not appid:
        return None
    art_dir = _art_dir(config)
    dest = art_dir / f"steam-{appid}.jpg"
    fetch_steam_art(appid, dest)
    return str(dest)


def fetch_art_for_game(library: Library, game_id: int, config: dict) -> str | None:
    game = library.get_game(game_id)
    if not game:
        return None
    if game.artpath:
        return game.artpath

    path = fetch_art_for_path(game.path, config)
    if not path:
        return None
    library.update_game(game.id, {"artpath": path})
    return path
