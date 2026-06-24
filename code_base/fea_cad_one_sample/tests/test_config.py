"""Unit tests for the local config loader wrapper."""

# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import DEFAULT_CONFIG_NAME, load_config


def test_load_config_uses_default_file_and_expands_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_config loads the default config and expands env placeholders."""

    monkeypatch.setenv("CAD_DB_CONNECTION_STRING", "postgresql://example/db")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

    config = load_config()

    assert config["version"] == 2
    assert config["db"]["connection_string"] == "postgresql://example/db"
    assert config["model"]["api_key"] == "test-openai-key"
    assert config["analysis"]["classifier_api_key"] == "test-openai-key"
    assert config["computation_graph"]["api_key"] == "test-openai-key"
    assert DEFAULT_CONFIG_NAME == "config_gpt_5_4_mini.yaml"


def test_load_config_expands_env_vars_recursively(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """load_config expands env vars inside nested YAML mappings and lists."""

    monkeypatch.setenv("FOO", "alpha")
    monkeypatch.setenv("BAR", "beta")
    config_path = tmp_path / "custom.yaml"
    config_path.write_text(
        """
root:
  nested:
    value: ${FOO}
  items:
    - keep
    - ${BAR}
""",
        encoding="utf-8",
    )

    config = load_config(config_name=config_path.name, config_dir=tmp_path)

    assert config == {"root": {"nested": {"value": "alpha"}, "items": ["keep", "beta"]}}


def test_load_config_missing_file_raises_clear_error(tmp_path: Path) -> None:
    """load_config raises a clear FileNotFoundError when the file is missing."""

    with pytest.raises(FileNotFoundError, match=r"Config file not found: .*missing\.yaml"):
        load_config(config_name="missing.yaml", config_dir=tmp_path)
