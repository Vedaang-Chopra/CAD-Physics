"""Local config loader wrapper for the one-sample FEA prototype."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_NAME = "config_gpt_5_4_mini.yaml"
_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent / "copied_from_cadcodeverify" / "configs"
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def load_config(
    config_name: str | Path = DEFAULT_CONFIG_NAME,
    config_dir: Path | None = None,
) -> dict[str, Any]:
    """Load a YAML config and expand environment-variable placeholders."""

    logger.info(
        "load_config | start | config_name=%s | config_dir=%s",
        config_name,
        config_dir,
    )
    try:
        config_path = _resolve_config_path(config_name=config_name, config_dir=config_dir)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with config_path.open("r", encoding="utf-8") as handle:
            raw_config = yaml.safe_load(handle) or {}

        if not isinstance(raw_config, dict):
            raise ValueError(f"Config file must contain a YAML mapping: {config_path}")

        expanded_config = _expand_env_vars(raw_config)
        logger.info(
            "load_config | done | config_path=%s | keys=%s",
            config_path,
            sorted(expanded_config.keys()),
        )
        return expanded_config
    except Exception:
        logger.exception(
            "load_config | failed | config_name=%s | config_dir=%s",
            config_name,
            config_dir,
        )
        raise


def _resolve_config_path(
    config_name: str | Path,
    config_dir: Path | None,
) -> Path:
    """Resolve the path to a config file."""

    config_path = Path(config_name)
    if config_path.is_absolute() or config_path.parent != Path("."):
        return config_path.expanduser()

    base_dir = config_dir or _DEFAULT_CONFIG_DIR
    return (base_dir / config_path.name).expanduser()


def _expand_env_vars(value: Any) -> Any:
    """Recursively expand ${VAR} placeholders in YAML values."""

    if isinstance(value, dict):
        return {key: _expand_env_vars(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_expand_env_vars(item) for item in value)
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda match: os.environ.get(match.group(1), match.group(0)), value)
    return value
