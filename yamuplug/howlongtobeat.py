from __future__ import annotations

from typing import Any

from howlongtobeatpy import HowLongToBeat

from yamu.importer.pipeline import ImportCandidate
from yamuplug import register_import_provider


class HowLongToBeatError(RuntimeError):
    pass


_FIELD_MAP = {
    "main_story": "hltb_main_story",
    "main_extra": "hltb_main_extra",
    "completionist": "hltb_completionist",
}


def _config_section(config: dict) -> dict:
    section = config.get("howlongtobeat", {})
    return section if isinstance(section, dict) else {}


def _get_service(config: dict) -> HowLongToBeat:
    section = _config_section(config)
    minimum_similarity = float(section.get("minimum_similarity", 0.4) or 0.4)
    auto_filter_times = bool(section.get("auto_filter_times", False))
    return HowLongToBeat(minimum_similarity, auto_filter_times)


def _entry_value(entry: Any, name: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(name)
    return getattr(entry, name, None)


def _to_hours(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _candidate_fields(entry: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for source, target in _FIELD_MAP.items():
        value = _to_hours(_entry_value(entry, source))
        if value is not None:
            fields[target] = value
    return fields


def fetch_hltb_fields(title: str, config: dict) -> dict[str, Any]:
    service = _get_service(config)
    similarity_case_sensitive = bool(
        _config_section(config).get("similarity_case_sensitive", False)
    )
    try:
        results = service.search(
            str(title),
            similarity_case_sensitive=similarity_case_sensitive,
        )
    except Exception as exc:
        raise HowLongToBeatError(str(exc)) from exc
    if not results:
        return {}
    best = max(results, key=lambda entry: getattr(entry, "similarity", -1) or -1)
    return _candidate_fields(best)


class HowLongToBeatImportProvider:
    name = "howlongtobeat"

    def tasks(self, _config: dict):
        return iter(())

    def search(self, game, config: dict):
        title = getattr(game, "title", None)
        if not title:
            return []
        fields = fetch_hltb_fields(str(title), config)
        if not fields:
            return []
        return [ImportCandidate(fields=fields)]


register_import_provider(HowLongToBeatImportProvider())
