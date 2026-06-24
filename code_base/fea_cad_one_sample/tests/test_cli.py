"""Unit tests for the one-sample FEA CLI."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.main import main


def test_inspect_schema_cli_prints_readable_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """inspect-schema prints a readable schema summary."""

    db_path = tmp_path / "schema.db"
    connection_string = f"sqlite:///{db_path}"

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE master_metadata (id TEXT PRIMARY KEY, expert_prompt TEXT)"
        )
        connection.execute(
            "CREATE TABLE ground_truth_code (id TEXT PRIMARY KEY, python_code TEXT)"
        )
        connection.commit()

    monkeypatch.setenv("CAD_DB_CONNECTION_STRING", connection_string)

    exit_code = main(["inspect-schema", "--config", "config_gpt_5_4_mini.yaml"])

    output = capsys.readouterr()
    assert exit_code == 0
    assert "Schema summary" in output.out
    assert "Dialect:" in output.out
    assert "master_metadata" in output.out
    assert "ground_truth_code" in output.out
    assert "expert_prompt" in output.out
    assert output.err == ""


def test_inspect_schema_cli_rejects_missing_connection_string(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """inspect-schema fails cleanly when the DB connection string is missing."""

    monkeypatch.delenv("CAD_DB_CONNECTION_STRING", raising=False)

    exit_code = main(["inspect-schema", "--config", "config_gpt_5_4_mini.yaml"])

    output = capsys.readouterr()
    assert exit_code == 1
    assert "CAD_DB_CONNECTION_STRING" in output.err
    assert output.out == ""


def test_inspect_schema_cli_passes_force_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI accepts --force and forwards it to the inspect-schema runner."""

    captured: dict[str, object] = {}

    def fake_run_inspect_schema(config_name: str, force: bool = False) -> int:
        captured["config_name"] = config_name
        captured["force"] = force
        return 0

    monkeypatch.setattr("src.main._run_inspect_schema", fake_run_inspect_schema)

    exit_code = main(["--force", "inspect-schema", "--config", "config_gpt_5_4_mini.yaml"])

    assert exit_code == 0
    assert captured["config_name"] == "config_gpt_5_4_mini.yaml"
    assert captured["force"] is True


def test_inspect_schema_cli_rejects_sample_selection_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """inspect-schema rejects sample-selection flags before running."""

    exit_code = main([
        "inspect-schema",
        "--config",
        "config_gpt_5_4_mini.yaml",
        "--sample-id",
        "sample-001",
    ])

    output = capsys.readouterr()
    assert exit_code == 1
    assert "does not accept sample-selection flags" in output.err


def test_build_freecad_instructions_cli_passes_force_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI forwards --force to write commands that create artifacts."""

    captured: dict[str, object] = {}

    def fake_runner(config_name: str, sample_id: str, force: bool) -> dict[str, str]:
        captured["config_name"] = config_name
        captured["sample_id"] = sample_id
        captured["force"] = force
        return {"freecad_instructions_path": "/tmp/freecad_instructions.md"}

    monkeypatch.setattr("src.main.runners.build_freecad_instructions_only_runner", fake_runner)

    exit_code = main([
        "build-freecad-instructions",
        "--config",
        "config_gpt_5_4_mini.yaml",
        "--sample-id",
        "sample-001",
        "--force",
    ])

    assert exit_code == 0
    assert captured["config_name"] == "config_gpt_5_4_mini.yaml"
    assert captured["sample_id"] == "sample-001"
    assert captured["force"] is True


def test_run_cli_rejects_missing_selection_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run rejects missing sample-selection flags before pipeline execution."""

    exit_code = main([
        "run",
        "--config",
        "config_gpt_5_4_mini.yaml",
    ])

    output = capsys.readouterr()
    assert exit_code == 1
    assert "requires exactly one" in output.err


def test_run_cli_rejects_conflicting_selection_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run rejects conflicting sample-selection flags before pipeline execution."""

    exit_code = main([
        "run",
        "--config",
        "config_gpt_5_4_mini.yaml",
        "--sample-id",
        "sample-001",
        "--random",
    ])

    output = capsys.readouterr()
    assert exit_code == 1
    assert "requires exactly one" in output.err


def test_cli_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """--help exits cleanly."""

    exit_code = main(["--help"])
    output = capsys.readouterr()
    assert exit_code == 0
    assert "One-sample CAD-to-FEA prototype CLI." in output.out
