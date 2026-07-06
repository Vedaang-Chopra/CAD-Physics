"""Utility helpers for the FEA replication pipeline."""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any


def ensure_parent_dir(path: Path) -> Path:
    """Create the parent directory for a path and return the path."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, text: str, *, force: bool = False) -> Path:
    """Write UTF-8 text to a file, refusing to overwrite unless forced."""

    path = Path(path)
    if path.exists() and not force:
        raise FileExistsError(f"Existing file found at {path}. Use force=True to overwrite.")
    ensure_parent_dir(path)
    path.write_text((text or "").rstrip() + "\n", encoding="utf-8")
    return path


def write_json(path: Path, payload: Any, *, force: bool = False) -> Path:
    """Write JSON to disk with stable formatting."""

    path = Path(path)
    if path.exists() and not force:
        raise FileExistsError(f"Existing file found at {path}. Use force=True to overwrite.")
    ensure_parent_dir(path)
    path.write_text(json.dumps(to_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def to_jsonable(value: Any) -> Any:
    """Convert dataclasses, paths, and containers into JSON-safe values."""

    if is_dataclass(value):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    return value


def chunked(items: list[Any], size: int) -> list[list[Any]]:
    """Split a list into fixed-size chunks."""

    if size <= 0:
        raise ValueError("chunk size must be positive")
    return [items[index : index + size] for index in range(0, len(items), size)]
