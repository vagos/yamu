from __future__ import annotations

from importlib import import_module

from yamu.util.color import warning
from typing import Iterable, List, Protocol

from yamu.importer.pipeline import ImportTask


class ImportProvider(Protocol):
    name: str

    def tasks(self, config: dict) -> Iterable[ImportTask]: ...


_IMPORT_PROVIDERS: List[ImportProvider] = []
_LOADED_PLUGINS: set[str] = set()


def register_import_provider(provider: ImportProvider) -> None:
    _IMPORT_PROVIDERS.append(provider)


def import_providers() -> List[ImportProvider]:
    return list(_IMPORT_PROVIDERS)


def load_plugins(names: Iterable[str]) -> None:
    for name in names:
        if name in _LOADED_PLUGINS:
            continue
        try:
            import_module(f"yamuplug.{name}")
        except ModuleNotFoundError:
            print(warning(f"Plugin not found: {name}"))
            continue
        _LOADED_PLUGINS.add(name)


__all__ = [
    "import_providers",
    "register_import_provider",
    "load_plugins",
    "ImportProvider",
]
