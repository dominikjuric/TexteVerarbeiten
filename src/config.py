"""Configuration loading utilities for the PDF pipeline."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONFIG: Dict[str, Any] = {
    "paths": {
        "raw": "raw",
        "text": "txt",
        "processed": "processed",
        "metadata": "metadata",
        "logs": "logs",
        "chroma": ".chroma",
        "whoosh_index": "processed/whoosh_index",
    },
    "models": {
        "chat": "gpt-4o-mini",
        "embedding": "all-MiniLM-L6-v2",
        "nougat": "facebook/nougat-base",
    },
    "services": {
        "openai": {"api_key": ""},
        "mathpix": {"app_id": "", "app_key": ""},
        "zotero": {"user_id": "", "api_key": ""},
    },
    "pipeline": {
        "default_batch_size": 8,
        "default_index_batch_size": 200,
        "overwrite_outputs": False,
    },
    "rag": {
        "collection": "papers",
        "persist_path": ".chroma",
        "history_limit": 10,
        "temperature": 0.0,
        "results_per_query": 5,
    },
    "formulas": {
        "markdown_dir": "processed/nougat_md",
        "text_dir": "processed/nougat_txt",
        "metadata_file": "metadata/formulas.jsonl",
        "index_db": "metadata/formula_index.sqlite",
    },
}

ENVIRONMENT_OVERRIDES: Mapping[tuple[str, ...], str] = {
    ("services", "openai", "api_key"): "OPENAI_API_KEY",
    ("services", "mathpix", "app_id"): "MATHPIX_APP_ID",
    ("services", "mathpix", "app_key"): "MATHPIX_APP_KEY",
    ("services", "zotero", "user_id"): "ZOTERO_USER_ID",
    ("services", "zotero", "api_key"): "ZOTERO_API_KEY",
}


def _candidate_paths() -> Iterable[Path]:
    """Yield candidate configuration files ordered by precedence."""

    env_path = os.getenv("PIPELINE_CONFIG_PATH")
    if env_path:
        yield Path(env_path).expanduser()

    root = Path(__file__).resolve().parent.parent
    yield root / "config.json"
    yield root / "config" / "config.json"
    yield root / "config" / "config.local.json"
    yield root / "config" / "config.example.json"


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _deep_update(base: MutableMapping[str, Any], updates: Mapping[str, Any]) -> MutableMapping[str, Any]:
    for key, value in updates.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), MutableMapping):
            _deep_update(base[key], value)  # type: ignore[index]
        else:
            base[key] = value
    return base


def _set_nested(target: MutableMapping[str, Any], keys: Iterable[str], value: Any) -> None:
    keys = list(keys)
    cursor: MutableMapping[str, Any] = target
    for key in keys[:-1]:
        existing = cursor.get(key)
        if not isinstance(existing, MutableMapping):
            existing = {}
            cursor[key] = existing
        cursor = existing  # type: ignore[assignment]
    cursor[keys[-1]] = value


def load_config() -> Dict[str, Any]:
    """Return the merged configuration using defaults, files and environment."""

    config: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)

    for path in _candidate_paths():
        if path.is_file():
            data = _load_json(path)
            if not isinstance(data, Mapping):
                raise ValueError(f"Konfigurationsdatei {path} enthält kein Objekt.")
            _deep_update(config, data)  # type: ignore[arg-type]

    for keys, env_key in ENVIRONMENT_OVERRIDES.items():
        value = os.getenv(env_key)
        if value:
            _set_nested(config, keys, value)

    return config


def resolve_path(key: str) -> Path:
    """Resolve a configured path entry to an absolute :class:`Path`."""

    path_value = CFG.get("paths", {}).get(key)
    if not path_value:
        raise KeyError(f"Pfad '{key}' ist in der Konfiguration nicht definiert.")
    return Path(path_value).expanduser().resolve()


CFG = load_config()

__all__ = ["CFG", "load_config", "resolve_path"]
