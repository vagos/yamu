from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any

from yamu.importer.pipeline import ImportCandidate, ImportTask
from yamuplug import register_import_provider


IGDB_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_GAMES_URL = "https://api.igdb.com/v4/games"


class IgdbError(RuntimeError):
    pass


def _get_client_id(config: dict | None = None) -> str:
    if "IGDB_CLIENT_ID" in os.environ:
        return os.environ["IGDB_CLIENT_ID"].strip()
    if config:
        return str(config.get("igdb", {}).get("client_id", "")).strip()
    return ""


def _get_client_secret(config: dict | None = None) -> str:
    if "IGDB_CLIENT_SECRET" in os.environ:
        return os.environ["IGDB_CLIENT_SECRET"].strip()
    if config:
        return str(config.get("igdb", {}).get("client_secret", "")).strip()
    return ""


def _token_cache_path(config: dict) -> str:
    raw = str(config.get("igdb", {}).get("token_cache_path", "")).strip()
    if raw:
        return os.path.expanduser(raw)
    base = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    return os.path.join(base, "yamu", "igdb_token.json")


def _load_token_cache(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return payload
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return {}


def _save_token_cache(path: str, payload: dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
    except OSError:
        return


def _fetch_token(client_id: str, client_secret: str) -> dict[str, Any]:
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(IGDB_TOKEN_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or "access_token" not in payload:
        raise IgdbError("Failed to fetch IGDB access token")
    return payload


def get_igdb_token(config: dict) -> str:
    access_token = str(config.get("igdb", {}).get("access_token", "")).strip()
    if access_token:
        return access_token
    client_id = _get_client_id(config)
    client_secret = _get_client_secret(config)
    if not client_id or not client_secret:
        raise IgdbError("IGDB client credentials are required")
    cache_path = _token_cache_path(config)
    cached = _load_token_cache(cache_path)
    now = int(time.time())
    token = cached.get("access_token")
    expires_at = int(cached.get("expires_at", 0) or 0)
    if token and expires_at > now:
        return str(token)
    payload = _fetch_token(client_id, client_secret)
    expires_in = int(payload.get("expires_in", 0) or 0)
    token = str(payload.get("access_token", "")).strip()
    if not token:
        raise IgdbError("IGDB token response missing access token")
    expires_at = now + max(0, expires_in - 60)
    _save_token_cache(cache_path, {"access_token": token, "expires_at": expires_at})
    return token


def fetch_igdb_games(term: str, config: dict, limit: int = 5) -> list[dict]:
    client_id = _get_client_id(config)
    token = get_igdb_token(config)
    query = (
        f'search "{term}"; '
        "fields name,first_release_date,genres.name,platforms.name,"
        "involved_companies.developer,involved_companies.publisher,"
        "involved_companies.company.name; "
        f"limit {max(1, limit)};"
    )
    req = urllib.request.Request(IGDB_GAMES_URL, data=query.encode("utf-8"))
    req.add_header("Client-ID", client_id)
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, list):
        return payload
    return []


def _release_date_from_timestamp(ts: int | None) -> str | None:
    if not ts:
        return None
    parsed = time.gmtime(int(ts))
    return f"{parsed.tm_year:04d}-{parsed.tm_mon:02d}-{parsed.tm_mday:02d}"


def _extract_genres(entry: dict) -> str | None:
    genres = entry.get("genres") or []
    if not isinstance(genres, list):
        return None
    names = [str(g.get("name")) for g in genres if isinstance(g, dict) and g.get("name")]
    if not names:
        return None
    return ", ".join(names)


def _extract_platforms(entry: dict) -> str | None:
    platforms = entry.get("platforms") or []
    if not isinstance(platforms, list):
        return None
    names = [str(p.get("name")) for p in platforms if isinstance(p, dict) and p.get("name")]
    if not names:
        return None
    return ", ".join(names)


def _extract_companies(entry: dict, flag: str) -> str | None:
    involved = entry.get("involved_companies") or []
    if not isinstance(involved, list):
        return None
    names = []
    for company in involved:
        if not isinstance(company, dict):
            continue
        if not company.get(flag):
            continue
        info = company.get("company") or {}
        if isinstance(info, dict) and info.get("name"):
            names.append(str(info.get("name")))
    if not names:
        return None
    return ", ".join(names)


def _candidate_fields(entry: dict) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    name = entry.get("name")
    if name:
        fields["title"] = str(name)
    fields["release_date"] = _release_date_from_timestamp(
        entry.get("first_release_date")
    )
    fields["genre"] = _extract_genres(entry)
    fields["platform"] = _extract_platforms(entry)
    fields["developer"] = _extract_companies(entry, "developer")
    fields["publisher"] = _extract_companies(entry, "publisher")
    return fields


class IgdbImportProvider:
    name = "igdb"

    def tasks(self, _config: dict):
        return iter(())

    def search(self, game, config: dict):
        limit = int(config.get("igdb", {}).get("search_limit", 5) or 5)
        term = getattr(game, "title", None)
        if not term:
            return []
        try:
            results = fetch_igdb_games(str(term), config, limit=limit)
        except Exception as exc:
            raise IgdbError(str(exc)) from exc
        candidates: list[ImportCandidate] = []
        for entry in results:
            if not isinstance(entry, dict):
                continue
            fields = _candidate_fields(entry)
            if fields:
                candidates.append(ImportCandidate(fields=fields))
        return candidates


register_import_provider(IgdbImportProvider())
