from __future__ import annotations

import json
import subprocess
import time
from typing import Any, Iterable

from yamu.importer.pipeline import ImportCandidate, ImportTask
from yamuplug import register_import_provider


class EpicError(RuntimeError):
    pass


def _legendary_path(config: dict) -> str:
    return str(config.get("epic", {}).get("legendary_path", "")).strip() or "legendary"


def _run_legendary(args: Iterable[str], config: dict) -> str:
    cmd = [_legendary_path(config), *args]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip()
        raise EpicError(message or "legendary failed")
    return proc.stdout


def fetch_owned_games(config: dict) -> list[dict]:
    output = _run_legendary(["list", "--json"], config)
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise EpicError("legendary returned invalid JSON") from exc
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("games") or payload.get("data")
        if isinstance(items, list):
            return items
    return []


def fetch_game_info(app_name: str, config: dict) -> dict[str, Any]:
    output = _run_legendary(["info", "--json", app_name], config)
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise EpicError("legendary info returned invalid JSON") from exc
    if isinstance(payload, dict):
        return payload
    return {}


def _extract_app_name(entry: dict) -> str | None:
    for key in ("app_name", "appName", "appname", "app"):
        value = entry.get(key)
        if value:
            return str(value)
    return None


def _extract_title(entry: dict) -> str | None:
    for key in ("title", "name", "app_title", "appTitle"):
        value = entry.get(key)
        if value:
            return str(value)
    return None


def _normalize_release_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = time.gmtime(int(value))
        return f"{parsed.tm_year:04d}-{parsed.tm_mon:02d}-{parsed.tm_mday:02d}"
    raw = str(value).strip()
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return raw[:10]
    return raw or None


def _candidate_fields(entry: dict) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    title = _extract_title(entry)
    if title:
        fields["title"] = title
    fields["release_date"] = _normalize_release_date(
        entry.get("releaseDate") or entry.get("release_date")
    )
    for key, target in (
        ("developer", "developer"),
        ("publisher", "publisher"),
        ("developers", "developer"),
        ("publishers", "publisher"),
    ):
        value = entry.get(key)
        if value and target not in fields:
            if isinstance(value, list):
                fields[target] = ", ".join(str(v) for v in value if v)
            else:
                fields[target] = str(value)
    return fields


class EpicImportProvider:
    name = "epic"

    def tasks(self, config: dict):
        games = fetch_owned_games(config)
        for game in games:
            if not isinstance(game, dict):
                continue
            app_name = _extract_app_name(game)
            title = _extract_title(game)
            if not app_name or not title:
                continue
            fields = {
                "title": title,
                "platform": "epic",
                "path": f"epic://{app_name}",
            }
            yield ImportTask(original=fields)

    def search(self, game, config: dict):
        delay = float(config.get("epic", {}).get("delay", 0) or 0)
        app_name = None
        path = getattr(game, "path", None)
        if isinstance(path, str) and path.startswith("epic://"):
            app_name = path.split("epic://", 1)[1]
        if not app_name:
            return []
        details = fetch_game_info(app_name, config)
        fields = _candidate_fields(details)
        candidates = []
        if fields:
            candidates.append(ImportCandidate(fields=fields))
        if delay:
            time.sleep(delay)
        return candidates


register_import_provider(EpicImportProvider())
