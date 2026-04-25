from __future__ import annotations

import queue
import threading
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional

from yamu.library.library import Library
from yamu.library.models import GAME_FIELDS
from yamu.util.changes import show_model_changes
from yamu.util.color import colorize, error, info, warning
from yamu.util.prompt import input_options, input_options_with_numbers, input_yn
from yamu.util.edit_flow import edit_items_in_editor, diff_item, prompt_apply_changes


@dataclass
class ImportCandidate:
    fields: Dict[str, Any]
    source: str = "base"


@dataclass
class ImportTask:
    original: Dict[str, Any]


class Provider:
    def candidates(self, task: ImportTask) -> List[ImportCandidate]:
        return [ImportCandidate(fields=task.original)]


SIMILARITY_FIELDS = (
    "title",
    "platform",
    "release_date",
    "genre",
    "developer",
    "publisher",
    "region",
)

SIMILARITY_WEIGHTS = {
    "title": 5.0,
    "platform": 1.0,
    "release_date": 1.0,
    "genre": 1.0,
    "developer": 1.0,
    "publisher": 1.0,
    "region": 1.0,
}


def _normalize_similarity_value(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _string_similarity(left: Any, right: Any) -> float:
    normalized_left = _normalize_similarity_value(left)
    normalized_right = _normalize_similarity_value(right)
    if not normalized_left and not normalized_right:
        return 1.0
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(a=normalized_left, b=normalized_right).ratio()


def _candidate_similarity(base: Dict[str, Any], candidate: Dict[str, Any]) -> float:
    weighted_score = 0.0
    total_weight = 0.0
    for field in SIMILARITY_FIELDS:
        left = base.get(field)
        right = candidate.get(field)
        if left in (None, "") or right in (None, ""):
            continue
        weight = SIMILARITY_WEIGHTS.get(field, 1.0)
        weighted_score += _string_similarity(left, right) * weight
        total_weight += weight
    if total_weight:
        return weighted_score / total_weight
    return _string_similarity(base.get("title"), candidate.get("title"))


def _sort_candidates(
    base: Dict[str, Any], candidates: List[ImportCandidate]
) -> List[ImportCandidate]:
    return sorted(
        candidates,
        key=lambda candidate: _candidate_similarity(base, candidate.fields),
        reverse=True,
    )


def _similarity_color_name(similarity: float) -> str:
    if similarity >= 0.9:
        return "text_success"
    if similarity >= 0.7:
        return "text_warning"
    return "text_error"


def _similarity_string(similarity: float) -> str:
    return colorize(_similarity_color_name(similarity), f"{similarity * 100:.1f}%")


class Importer:
    def __init__(
        self,
        library: Library,
        provider: Provider | None = None,
        threads: int = 2,
        prompt_existing: bool = False,
    ) -> None:
        self.library = library
        self.provider = provider or Provider()
        self.threads = max(1, threads)
        self.prompt_existing = prompt_existing
        self._in_q: queue.Queue[Optional[ImportTask]] = queue.Queue()
        self._out_q: queue.Queue[Optional[tuple[ImportTask, List[ImportCandidate]]]] = (
            queue.Queue()
        )

    def _worker(self) -> None:
        while True:
            task = self._in_q.get()
            if task is None:
                self._out_q.put(None)
                self._in_q.task_done()
                break
            try:
                candidates = self.provider.candidates(task)
                self._out_q.put((task, candidates))
            finally:
                self._in_q.task_done()

    def _prompt(
        self,
        task: ImportTask,
        candidates: List[ImportCandidate],
        selected: int = 0,
    ) -> tuple[str, int]:
        if not candidates:
            print(warning("No candidates found."))
            return ("s", selected)

        title = str(task.original.get("title") or "Unknown")
        print("")
        print(f'Finding metadata for game "{title}".')
        incoming = self._summarize_fields(task.original)
        if incoming:
            print(f"  Incoming: {incoming}")

        if len(candidates) > 1:
            while True:
                print("  Candidates:")
                for idx, candidate in enumerate(candidates, start=1):
                    summary = self._summarize_fields(candidate.fields)
                    similarity = _similarity_string(
                        _candidate_similarity(task.original, candidate.fields)
                    )
                    label = f"{idx}."
                    if candidate.source and candidate.source != "base":
                        if summary:
                            summary = f"{summary} [{candidate.source}]"
                        else:
                            summary = f"[{candidate.source}]"
                    print(f"    {label} ({similarity}) {summary}")

                choice = input_options_with_numbers(
                    ("Skip", "Ignore", "Quit"),
                    len(candidates),
                )
                if choice.isdigit():
                    selected = int(choice) - 1
                    break
                if choice == "i":
                    if self._ignore_import(task.original):
                        return ("i", selected)
                    continue
                if choice == "q":
                    return ("q", selected)
                return ("s", selected)

        self._print_fields("Metadata", candidates[selected].fields)

        if len(candidates) > 1:
            choice = input_options(
                ("Accept", "More candidates", "Skip", "Edit", "Ignore", "Quit")
            )
        else:
            choice = input_options(("Accept", "Skip", "Edit", "Ignore", "Quit"))
        return (choice, selected)

    def _edit_candidate(self, candidate: ImportCandidate) -> ImportCandidate:
        edited = edit_items_in_editor([candidate.fields])
        if len(edited) != 1:
            raise ValueError("Edited file must contain one entry")
        entry = edited[0]
        if not isinstance(entry, dict):
            raise ValueError("Edited entry must be a mapping")
        allowed = set(GAME_FIELDS)
        cleaned = self._sanitize_entry(entry, allowed)
        return ImportCandidate(fields=cleaned)

    def _sanitize_entry(
        self, entry: Dict[str, Any], allowed: set[str]
    ) -> Dict[str, Any]:
        cleaned: Dict[str, Any] = {}
        for key, value in entry.items():
            if key not in allowed:
                continue
            cleaned[key] = value
        return cleaned

    def _updates_from_fields(
        self, fields: Dict[str, Any], exclude: set[str]
    ) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        for key, value in fields.items():
            if key in exclude or value is None or value == "":
                continue
            updates[key] = value
        return updates

    def _merge_missing_fields(
        self, current: Dict[str, Any], candidate: Dict[str, Any]
    ) -> Dict[str, Any]:
        merged = dict(current)
        for key, value in candidate.items():
            if value is None or value == "":
                continue
            if merged.get(key) not in (None, ""):
                continue
            merged[key] = value
        return merged

    def _apply_updates(
        self, game_id: int, fields: Dict[str, Any], exclude: set[str]
    ) -> bool:
        updates = self._updates_from_fields(fields, exclude)
        if not updates:
            return False
        self.library.update_game(game_id, updates)
        return True

    def _apply_diff(
        self,
        game_id: int,
        before: Dict[str, Any],
        after: Dict[str, Any],
        fields: List[str],
    ) -> bool:
        updates = diff_item(before, after, fields)
        if not updates:
            return False
        self.library.update_game(game_id, updates)
        return True

    def _apply_achievements(
        self, game_id: int, achievements: list[dict] | None
    ) -> None:
        if achievements is None:
            return
        if achievements:
            self.library.upsert_achievements(game_id, achievements)

    def _ignore_import(self, fields: Dict[str, Any]) -> bool:
        path = fields.get("path")
        if not path:
            print(warning("Cannot ignore an import without a path."))
            return False
        title = str(fields.get("title") or "Unknown")
        rendered_path = str(path)
        self.library.ignore_import_path(rendered_path, fields.get("title"))
        print(info(f'Ignoring future imports for "{title}" ({rendered_path}).'))
        return True

    def _game_fields(self, game: Any) -> Dict[str, Any]:
        return {field: getattr(game, field) for field in GAME_FIELDS}

    def _print_fields(self, title: str, data: Dict[str, Any]) -> None:
        print(f"\n{title}:")
        for key, value in data.items():
            rendered = self._render_value(key, value)
            if rendered is not None:
                print(f"  {key}: {rendered}")

    def _render_value(self, key: str, value: Any) -> str | None:
        if value is None:
            return None
        if key == "achievements" and isinstance(value, list):
            return f"[{len(value)} achievements]"
        return str(value)

    def _summarize_fields(self, fields: Dict[str, Any]) -> str:
        title = fields.get("title")
        platform = fields.get("platform")
        release_date = fields.get("release_date")
        parts = []
        if title:
            parts.append(str(title))
        if platform:
            parts.append(str(platform))
        if release_date:
            parts.append(str(release_date))
        return " - ".join(parts)

    def prompt_existing_update(
        self, existing: Any, candidates: List[ImportCandidate]
    ) -> tuple[int, bool]:
        current = self._game_fields(existing)
        candidates = _sort_candidates(current, candidates)
        if not candidates:
            return 0, False
        selected = 0
        if len(candidates) > 1:
            while True:
                self._print_fields("Current entry", current)
                print("\nCandidates:")
                for idx, candidate in enumerate(candidates, start=1):
                    similarity = _similarity_string(
                        _candidate_similarity(current, candidate.fields)
                    )
                    print(f"  Candidate {idx} ({similarity}):")
                    for key, value in candidate.fields.items():
                        rendered = self._render_value(key, value)
                        if rendered is not None:
                            print(f"    {key}: {rendered}")
                choice = input_options_with_numbers(
                    ("Skip", "Ignore", "Quit"),
                    len(candidates),
                    default="s",
                )
                if choice.isdigit():
                    selected = int(choice) - 1
                    break
                if choice == "i":
                    if self._ignore_import(current):
                        return 0, False
                    continue
                if choice == "q":
                    return 0, True
                return 0, False
        candidate = candidates[selected]
        proposed = dict(current)
        for key, value in candidate.fields.items():
            if value is None or value == "":
                continue
            proposed[key] = value
        proposed["id"] = existing.id
        merged = self._merge_missing_fields(current, candidate.fields)
        merged["id"] = existing.id
        fields = [field for field in GAME_FIELDS if field != "id"]
        if not diff_item(current, proposed, fields):
            return 0, False
        if len(candidates) == 1:
            self._print_fields("Current entry", current)
        self._print_fields("Fetched entry", candidate.fields)
        while True:
            choice = prompt_apply_changes(
                [(f"id {existing.id}", current, proposed)],
                fields,
                include_merge=True,
                include_ignore=True,
            )
            if choice in {"n", "c"}:
                return 0, False
            if choice == "a":
                updated = self._apply_diff(existing.id, current, proposed, fields)
                if updated:
                    self._apply_achievements(
                        existing.id, candidate.fields.get("achievements")
                    )
                return (1 if updated else 0), False
            if choice == "m":
                updated = self._apply_diff(existing.id, current, merged, fields)
                if updated:
                    self._apply_achievements(
                        existing.id, candidate.fields.get("achievements")
                    )
                return (1 if updated else 0), False
            if choice == "i":
                if self._ignore_import(current):
                    return 0, False
                continue
            if choice == "e":
                try:
                    edited = edit_items_in_editor([proposed])
                except Exception as exc:
                    print(error(f"Edit failed: {exc}"))
                    if not input_yn("Edit again? (Y/n)", require=False):
                        return 0, False
                    continue
                if len(edited) != 1:
                    print(error("Edited list length does not match original"))
                    if not input_yn("Edit again? (Y/n)", require=False):
                        return 0, False
                    continue
                entry = edited[0]
                if entry.get("id") != existing.id:
                    print(error("Edited entry must include the original id"))
                    if not input_yn("Edit again? (Y/n)", require=False):
                        return 0, False
                    continue
                allowed = set(GAME_FIELDS + ["id"])
                proposed = self._sanitize_entry(entry, allowed)
                continue
        return 0, False

    def _produce(self, task_source: Iterable[ImportTask]) -> None:
        for task in task_source:
            self._in_q.put(task)
        for _ in range(self.threads):
            self._in_q.put(None)

    def run(self, task_source: Iterable[ImportTask]) -> tuple[int, int]:
        return self.run_with_hooks(task_source)

    def run_with_hooks(
        self,
        task_source: Iterable[ImportTask],
        *,
        on_imported: Any | None = None,
        on_existing: Any | None = None,
        tick: Any | None = None,
    ) -> tuple[int, int]:
        workers = [
            threading.Thread(target=self._worker, daemon=True)
            for _ in range(self.threads)
        ]
        for worker in workers:
            worker.start()
        producer = threading.Thread(
            target=self._produce, args=(task_source,), daemon=True
        )
        producer.start()

        completed = 0
        updated = 0
        done_workers = 0
        while done_workers < self.threads:
            item = self._out_q.get()
            if item is None:
                done_workers += 1
                continue
            task, candidates = item
            candidates = _sort_candidates(task.original, candidates)

            path = task.original.get("path")
            existing = self.library.get_game_by_path(str(path)) if path else None
            if existing:
                if on_existing is not None:
                    on_existing(existing)
                if not self.prompt_existing:
                    if self._apply_updates(
                        existing.id, task.original, {"path", "title"}
                    ):
                        updated += 1
                    self._apply_achievements(
                        existing.id, task.original.get("achievements")
                    )
                    continue
                updated_count, should_quit = self.prompt_existing_update(
                    existing, candidates
                )
                updated += updated_count
                if tick is not None:
                    tick()
                if should_quit:
                    return completed, updated
                continue

            if not candidates:
                continue
            selected = 0
            while True:
                action, selected = self._prompt(task, candidates, selected)
                if action == "m":
                    continue
                if action == "a":
                    game = self.library.add_game(candidates[selected].fields)
                    completed += 1
                    self._apply_achievements(
                        game.id, candidates[selected].fields.get("achievements")
                    )
                    if on_imported is not None:
                        on_imported(game)
                    break
                if action == "s":
                    break
                if action == "i":
                    if self._ignore_import(task.original):
                        break
                    continue
                if action == "e":
                    try:
                        edited = self._edit_candidate(candidates[selected])
                    except Exception as exc:
                        print(error(f"Edit failed: {exc}"))
                        continue
                    print(info("Changes:"))
                    changed = show_model_changes(
                        candidates[selected].fields,
                        edited.fields,
                        GAME_FIELDS,
                        header="candidate",
                    )
                    if not changed:
                        print(info("No changes to apply."))
                        continue
                    if not input_yn("Apply edited changes? (Y/n)", require=False):
                        continue
                    game = self.library.add_game(edited.fields)
                    completed += 1
                    self._apply_achievements(game.id, edited.fields.get("achievements"))
                    if on_imported is not None:
                        on_imported(game)
                    break
                if action == "q":
                    return completed, updated
                print(warning("Unknown choice."))
                continue
            if tick is not None:
                tick()

        return completed, updated
