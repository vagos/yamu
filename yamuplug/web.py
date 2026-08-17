from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape
from yamu.library.library import Library
from yamu.library.models import all_game_fields
from yamu.util.config import load_config
from yamu.util.query import build_query
from yamuplug import YamuPlugin
from yamuplug.steam import list_achievements


def _asset_path(rel: str) -> Path:
    return Path(__file__).parent / "web" / rel


def _resolve_static_path(rel: str) -> Path | None:
    root = _asset_path("static").resolve()
    path = (root / rel).resolve()
    if path == root or root in path.parents:
        return path
    return None


def _content_type_for_path(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".css":
        return "text/css"
    if ext == ".js":
        return "text/javascript"
    if ext == ".html":
        return "text/html"
    return "application/octet-stream"


def _format_release_date(value: str | None, fmt: str) -> str | None:
    if not value:
        return None
    year_match = None
    for part in value.replace(",", " ").split():
        if len(part) == 4 and part.isdigit():
            year_match = part
            break
    return fmt.replace("$year", year_match or "").replace("$date", value)


def _template_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_asset_path("templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )


def _render_template(name: str, **context: object) -> bytes:
    env = _template_env()
    template = env.get_template(name)
    return template.render(**context).encode("utf-8")


def _rep(game) -> dict:
    fmt = _load_ui_date_format()
    release_date = _format_release_date(game.release_date, fmt)
    rep = {
        "id": game.id,
        "title": game.title,
        "platform": game.platform,
        "genre": game.genre,
        "developer": game.developer,
        "publisher": game.publisher,
        "region": game.region,
        "path": game.path,
        "collection": game.collection,
        "status": game.status,
        "artpath": game.artpath,
        "release_date": release_date,
    }
    for field in all_game_fields():
        if field not in rep:
            rep[field] = getattr(game, field, None)
    return rep


def _load_ui_date_format() -> str:
    try:
        from yamu.util.config import load_config
    except Exception:
        return "$year"
    cfg = load_config()
    return str(cfg.get("ui", {}).get("date_format", "$year"))


class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/index"):
            body = _render_template("index.html", title="yamu")
            self._send(200, body, "text/html")
            return

        if self.path.startswith("/static/"):
            rel = self.path[len("/static/") :]
            path = _resolve_static_path(rel)
            if path is None:
                self._send_json(404, {"error": "not found"})
                return
            self._send_file_path(200, path)
            return

        if self.path.startswith("/api/games/"):
            try:
                tail = self.path.split("/api/games/")[1]
                game_id = int(tail.split("/")[0].split("?")[0])
            except ValueError:
                self._send_json(404, {"error": "not found"})
                return
            if self.path.endswith("/art"):
                game = self.server.library.get_game(game_id)
                if not game or not game.artpath:
                    self._send_json(404, {"error": "not found"})
                    return
                art_path = Path(game.artpath)
                if not art_path.exists():
                    self._send_json(404, {"error": "not found"})
                    return
                self._send_file(200, art_path, _content_type_for_path(art_path))
                return
            if self.path.endswith("/achievements"):
                achievements = list_achievements(self.server.library, game_id)
                self._send_json(200, {"achievements": achievements})
                return
            game = self.server.library.get_game(game_id)
            if not game:
                self._send_json(404, {"error": "not found"})
                return
            self._send_json(200, _rep(game))
            return

        if self.path.startswith("/api/games"):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            allowed_fields = set(all_game_fields() + ["id", "status", "artpath"])
            parts = query.split() if query else []
            try:
                q = build_query(parts, allowed_fields)
                games = self.server.library.list_games(q)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            payload = {"games": [_rep(game) for game in games]}
            self._send_json(200, payload)
            return

        self._send_json(404, {"error": "not found"})

    def log_message(self, format: str, *args) -> None:
        return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self._send(code, body, "application/json")

    def _send_file(self, code: int, path: Path, content_type: str) -> None:
        self._send(code, path.read_bytes(), content_type)

    def _send_file_path(self, code: int, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json(404, {"error": "not found"})
            return
        content_type = _content_type_for_path(path)
        self._send(code, path.read_bytes(), content_type)


class WebServer(HTTPServer):
    def __init__(self, server_address: tuple[str, int], library: Library) -> None:
        super().__init__(server_address, WebHandler)
        self.library = library


def run_server(library: Library, host: str, port: int) -> None:
    server = WebServer((host, port), library)
    print(f"Serving Yamu library on http://{host}:{port}")
    server.serve_forever()


class WebPlugin(YamuPlugin):
    def commands(self):
        return [add_subparser]


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("web", help="Browse the library in a web UI")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, library: Library) -> int:
    config = load_config()
    web_cfg = config.get("web", {})
    host = args.host or web_cfg.get("host", "127.0.0.1")
    port = args.port or int(web_cfg.get("port", 8337))
    run_server(library, host, port)
    return 0
