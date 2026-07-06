"""Unit tests for DB schema inspection and sample loading helpers."""

# pyright: reportMissingImports=false

from __future__ import annotations

import json
from types import SimpleNamespace

import pandas as pd
import pytest

from src.db.load_sample import (
    load_expert_random_sample,
    load_random_sample,
    load_sample,
    load_sample_by_id,
)
from src.db.schema_inspection import inspect_schema
from src.schemas.sample import CADSample


class _FakeInspector:
    def __init__(self, tables: dict[str, list[dict[str, object]]]) -> None:
        self._tables = tables

    def get_table_names(self) -> list[str]:
        return list(self._tables.keys())

    def get_columns(self, table_name: str) -> list[dict[str, object]]:
        return self._tables[table_name]


class _FakeEngine:
    def __init__(self, dialect_name: str = "postgresql") -> None:
        self.dialect = SimpleNamespace(name=dialect_name)
        self.disposed = False

    def dispose(self) -> None:
        self.disposed = True


def test_inspect_schema_returns_serializable_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """inspect_schema returns a JSON-serializable table and column summary."""

    fake_engine = _FakeEngine()
    fake_inspector = _FakeInspector(
        {
            "master_metadata": [
                {"name": "id", "type": "VARCHAR", "nullable": False, "primary_key": True},
                {"name": "expert_prompt", "type": "TEXT", "nullable": True},
            ],
            "ground_truth_code": [
                {"name": "id", "type": "VARCHAR", "nullable": False, "primary_key": True},
            ],
        }
    )

    monkeypatch.setattr("src.db.schema_inspection.create_engine", lambda connection_string: fake_engine)
    monkeypatch.setattr("src.db.schema_inspection.inspect", lambda engine: fake_inspector)

    summary = inspect_schema("postgresql://example/db")

    assert summary["dialect"] == "postgresql"
    assert summary["table_count"] == 2
    assert [table["name"] for table in summary["tables"]] == ["ground_truth_code", "master_metadata"]
    assert summary["tables"][1]["columns"][0]["primary_key"] is True
    assert json.loads(json.dumps(summary)) == summary
    assert fake_engine.disposed is True


def test_inspect_schema_handles_empty_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """inspect_schema returns an empty summary when there are no tables."""

    fake_engine = _FakeEngine(dialect_name="sqlite")
    fake_inspector = _FakeInspector({})

    monkeypatch.setattr("src.db.schema_inspection.create_engine", lambda connection_string: fake_engine)
    monkeypatch.setattr("src.db.schema_inspection.inspect", lambda engine: fake_inspector)

    summary = inspect_schema("sqlite:///example.db")

    assert summary == {"dialect": "sqlite", "table_count": 0, "tables": []}
    assert fake_engine.disposed is True


def test_inspect_schema_rejects_empty_connection_string() -> None:
    """inspect_schema raises ValueError for a missing connection string."""

    with pytest.raises(ValueError, match="non-empty database URL"):
        inspect_schema("   ")


def test_load_sample_by_id_prefers_expert_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_sample_by_id returns the expert prompt when it exists."""

    calls: list[str] = []
    frame = pd.DataFrame(
        [
            {
                "sample_id": "sample-001",
                "expert_prompt": "Design a bracket.",
                "non_expert_prompt": "Design something decorative.",
                "ground_truth_code": "print('gt')",
            }
        ]
    )

    def fake_read_sql_dataframe(query: str, params: dict[str, object], connection_string: str) -> pd.DataFrame:
        calls.append(query)
        return frame

    monkeypatch.setattr("src.db.load_sample.read_sql_dataframe", fake_read_sql_dataframe)

    sample = load_sample_by_id("postgresql://example/db", "sample-001")

    assert isinstance(sample, CADSample)
    assert sample.sample_id == "sample-001"
    assert sample.prompt == "Design a bracket."
    assert sample.prompt_variant == "expert"
    assert sample.source == "cadcodeverify-db"
    assert sample.ground_truth_code == "print('gt')"
    assert sample.metadata["ground_truth_code"] == "print('gt')"
    assert sample.metadata["selection_mode"] == "sample_id"
    assert len(calls) == 1


def test_load_random_sample_uses_non_expert_prompt_when_needed(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_random_sample handles rows with only a non-expert prompt."""

    frame = pd.DataFrame(
        [
            {
                "sample_id": "sample-002",
                "expert_prompt": None,
                "non_expert_prompt": "Design a shelf support.",
                "ground_truth_code": "print('gt 2')",
            }
        ]
    )

    monkeypatch.setattr("src.db.load_sample.read_sql_dataframe", lambda *args, **kwargs: frame)

    sample = load_random_sample("postgresql://example/db")

    assert sample.sample_id == "sample-002"
    assert sample.prompt == "Design a shelf support."
    assert sample.prompt_variant == "non_expert"
    assert sample.metadata["selection_mode"] == "random"
    assert sample.ground_truth_code == "print('gt 2')"
    assert sample.metadata["prompt_variant"] == "non_expert"


def test_load_expert_random_sample_uses_fea_terms(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_expert_random_sample biases the SQL toward FEA-sensible prompts."""

    queries: list[str] = []
    frame = pd.DataFrame(
        [
            {
                "sample_id": "sample-003",
                "expert_prompt": "Design a bracket with a 200 N load.",
                "non_expert_prompt": None,
                "ground_truth_code": "print('gt 3')",
            }
        ]
    )

    def fake_read_sql_dataframe(query: str, params: dict[str, object], connection_string: str) -> pd.DataFrame:
        queries.append(query)
        return frame

    monkeypatch.setattr("src.db.load_sample.read_sql_dataframe", fake_read_sql_dataframe)

    sample = load_expert_random_sample("postgresql://example/db")

    assert sample.sample_id == "sample-003"
    assert sample.prompt_variant == "expert"
    assert sample.metadata["selection_mode"] == "expert_random"
    assert sample.ground_truth_code == "print('gt 3')"
    assert "bracket" in queries[0].lower()
    assert "expert_prompt" in queries[0]


def test_load_sample_rejects_missing_ground_truth_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_sample_by_id raises LookupError when the original CAD code is missing."""

    frame = pd.DataFrame(
        [
            {
                "sample_id": "sample-004",
                "expert_prompt": "Design a bracket.",
                "non_expert_prompt": None,
                "ground_truth_code": None,
            }
        ]
    )

    monkeypatch.setattr("src.db.load_sample.read_sql_dataframe", lambda *args, **kwargs: frame)

    with pytest.raises(LookupError, match="does not contain original CAD code"):
        load_sample_by_id("postgresql://example/db", "sample-004")


def test_load_sample_rejects_conflicting_selection_flags() -> None:
    """load_sample raises ValueError when selection flags conflict."""

    with pytest.raises(ValueError, match="exactly one of sample_id, random, or expert_random"):
        load_sample("postgresql://example/db", sample_id="sample-001", random=True)
