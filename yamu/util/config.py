from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict
import yaml

try:
    from importlib.resources import files
except ImportError:  # pragma: no cover
    from importlib_resources import files  # type: ignore


DEFAULT_CONFIG_NAME = "config.yaml"


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def user_config_path() -> Path:
    return _xdg_config_home() / "yamu" / DEFAULT_CONFIG_NAME


def _expand_path(value: str) -> str:
    return str(Path(os.path.expanduser(value)))


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text())
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


def _load_default() -> Dict[str, Any]:
    default_path = files("yamu").joinpath("config_default.yaml")
    data = yaml.safe_load(default_path.read_text())
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("Default config must be a mapping")
    return data


def load_config() -> Dict[str, Any]:
    default_cfg = _load_default()
    user_cfg = _load_yaml(user_config_path())
    merged = _deep_merge(default_cfg, user_cfg)

    library_value = merged.get("library", {})
    if isinstance(library_value, str):
        library = {"path": library_value}
    elif isinstance(library_value, dict):
        library = dict(library_value)
    else:
        library = {}
    if "path" in library:
        library["path"] = _expand_path(str(library["path"]))
    merged["library"] = library

    plugins_value = merged.get("plugins", [])
    if isinstance(plugins_value, str):
        merged["plugins"] = [plugins_value]
    elif isinstance(plugins_value, list):
        merged["plugins"] = [str(item) for item in plugins_value if item]
    else:
        merged["plugins"] = []
    return merged
