from __future__ import annotations

import inspect
from importlib import import_module
from typing import Any, Callable, Iterable, Protocol

from yamu.util.color import warning


PLUGIN_NAMESPACE = "yamuplug"


class ImportProvider(Protocol):
    name: str

    def tasks(self, config: dict) -> Iterable[Any]: ...


class PluginConflictError(Exception):
    pass


class PluginImportError(ImportError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Could not import plugin {name}")


class YamuPlugin:
    game_types: dict[str, str] = {}

    def __init__(self, name: str | None = None) -> None:
        self.name = name or self.__module__.split(".")[-1]

    def commands(self) -> list[Callable[[Any], None]]:
        return []

    def import_providers(self) -> list[ImportProvider]:
        return []

    def setup_library(self, _library: Any) -> None:
        return

    def handle_import_fields(
        self, _library: Any, _game_id: int, _fields: dict[str, Any]
    ) -> None:
        return

    def remove_game(self, _library: Any, _game_id: int) -> None:
        return


_instances: list[YamuPlugin] = []


def get_plugin_names() -> list[str]:
    from yamu.util.config import load_config

    config = load_config()
    names = config.get("plugins", [])
    if isinstance(names, str):
        return [names]
    if isinstance(names, list):
        return [str(name) for name in names]
    return []


def types(model_cls: type[Any]) -> dict[str, str]:
    return _types_for_name(model_cls.__name__.lower())


def _types_for_name(model_name: str) -> dict[str, str]:
    attr_name = f"{model_name}_types"
    fields: dict[str, str] = {}
    for plugin in find_plugins():
        plugin_types = getattr(plugin, attr_name, {})
        for name, sql_type in plugin_types.items():
            existing = fields.get(name)
            if existing is not None and existing != sql_type:
                raise PluginConflictError(
                    f"Plugin field {name} has already been defined with another type."
                )
            fields[name] = sql_type
    return fields


def import_providers() -> list[ImportProvider]:
    providers = []
    for plugin in find_plugins():
        providers.extend(plugin.import_providers())
    return providers


def commands() -> list[Callable[[Any], None]]:
    out: list[Callable[[Any], None]] = []
    for plugin in find_plugins():
        out.extend(plugin.commands())
    return out


def setup_library(library: Any) -> None:
    for plugin in find_plugins():
        plugin.setup_library(library)


def handle_import_fields(library: Any, game_id: int, fields: dict[str, Any]) -> None:
    for plugin in find_plugins():
        plugin.handle_import_fields(library, game_id, fields)


def remove_game(library: Any, game_id: int) -> None:
    for plugin in find_plugins():
        plugin.remove_game(library, game_id)


def find_plugins() -> Iterable[YamuPlugin]:
    return _instances


def load_plugins(names: Iterable[str] | None = None) -> None:
    if names is None:
        names = get_plugin_names()
    loaded = {plugin.name for plugin in _instances}
    for name in names:
        name = str(name)
        if name in loaded:
            continue
        plugin = _get_plugin(name)
        if plugin is not None:
            _instances.append(plugin)
            loaded.add(plugin.name)


def _get_plugin(name: str) -> YamuPlugin | None:
    try:
        module = import_module(f"{PLUGIN_NAMESPACE}.{name}")
    except ModuleNotFoundError as exc:
        if exc.name != f"{PLUGIN_NAMESPACE}.{name}":
            raise
        print(warning(f"Plugin not found: {name}"))
        return None

    for value in reversed(list(vars(module).values())):
        if (
            inspect.isclass(value)
            and issubclass(value, YamuPlugin)
            and value is not YamuPlugin
            and not inspect.isabstract(value)
            and (
                value.__module__ == module.__name__
                or value.__module__.startswith(f"{module.__name__}.")
            )
        ):
            return value()

    return YamuPlugin(name)
