from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from yamu.library.library import Library
from yamu.library.models import GAME_FIELDS
from yamu.util.changes import show_model_changes
from yamu.util.color import error, info, warning
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
                    label = f"{idx}."
                    if candidate.source and candidate.source != "base":
                        if summary:
                            summary = f"{summary} [{candidate.source}]"
                        else:
                            summary = f"[{candidate.source}]"
                    print(f"    {label} {summary}")

                choice = input_options_with_numbers(
                    ("Skip", "Quit"),
                    len(candidates),
                )
                if choice.isdigit():
                    selected = int(choice) - 1
                    break
                if choice == "q":
                    return ("q", selected)
                return ("s", selected)

        print("\nChanges:")
        changed = show_model_changes(
            task.original,
            candidates[selected].fields,
            GAME_FIELDS,
            header="",
        )
        if not changed:
            print(info("No changes."))

        if len(candidates) > 1:
            choice = input_options(
                ("Accept", "More candidates", "Skip", "Edit", "Quit")
            )
        else:
            choice = input_options(("Accept", "Skip", "Edit", "Quit"))
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
    ) -> int:
        if not candidates:
            return 0
        current = self._game_fields(existing)
        selected = 0
        if len(candidates) > 1:
            self._print_fields("Current entry", current)
            print("\nCandidates:")
            for idx, candidate in enumerate(candidates, start=1):
                print(f"  Candidate {idx}:")
                for key, value in candidate.fields.items():
                    rendered = self._render_value(key, value)
                    if rendered is not None:
                        print(f"    {key}: {rendered}")
            choice = input_options_with_numbers(
                ("Skip", "Quit"),
                len(candidates),
                default="s",
            )
            if choice.isdigit():
                selected = int(choice) - 1
            elif choice == "q":
                return 0
            else:
                return 0
        candidate = candidates[selected]
        proposed = dict(current)
        for key, value in candidate.fields.items():
            if value is None or value == "":
                continue
            proposed[key] = value
        proposed["id"] = existing.id
        fields = [field for field in GAME_FIELDS if field != "id"]
        if not diff_item(current, proposed, fields):
            return 0
        if len(candidates) == 1:
            self._print_fields("Current entry", current)
        self._print_fields("Fetched entry", candidate.fields)
        while True:
            choice = prompt_apply_changes(
                [(f"id {existing.id}", current, proposed)],
                fields,
            )
            if choice in {"n", "c"}:
                return 0
            if choice == "a":
                updated = self._apply_diff(existing.id, current, proposed, fields)
                if updated:
                    self._apply_achievements(
                        existing.id, candidate.fields.get("achievements")
                    )
                return 1 if updated else 0
            if choice == "e":
                try:
                    edited = edit_items_in_editor([proposed])
                except Exception as exc:
                    print(error(f"Edit failed: {exc}"))
                    if not input_yn("Edit again? (Y/n)", require=False):
                        return 0
                    continue
                if len(edited) != 1:
                    print(error("Edited list length does not match original"))
                    if not input_yn("Edit again? (Y/n)", require=False):
                        return 0
                    continue
                entry = edited[0]
                if entry.get("id") != existing.id:
                    print(error("Edited entry must include the original id"))
                    if not input_yn("Edit again? (Y/n)", require=False):
                        return 0
                    continue
                allowed = set(GAME_FIELDS + ["id"])
                proposed = self._sanitize_entry(entry, allowed)
                continue
        return 0

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
                updated += self.prompt_existing_update(existing, candidates)
                if tick is not None:
                    tick()
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
