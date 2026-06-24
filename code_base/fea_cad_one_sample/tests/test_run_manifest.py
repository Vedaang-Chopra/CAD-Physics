"""Unit tests for run-manifest helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.orchestration.manifest import (
    append_run_failure,
    create_run_manifest,
    finalize_run_manifest,
    initialize_run_manifest,
    load_run_manifest,
    update_run_manifest,
)
from src.schemas.pipeline import RUN_MANIFEST_ALLOWED_STATUSES


def test_create_and_initialize_run_manifest(tmp_path: Path) -> None:
    """create_run_manifest and initialize_run_manifest write the required top-level keys."""

    manifest_path = tmp_path / "run_manifest.json"
    manifest = create_run_manifest("sample-001", "config_gpt_5_4_mini.yaml", tmp_path / "outputs" / "sample_sample-001")
    initialized = initialize_run_manifest(
        manifest_path,
        "sample-001",
        "config_gpt_5_4_mini.yaml",
        tmp_path / "outputs" / "sample_sample-001",
    )

    assert set(manifest.keys()) == {
        "sample_id",
        "config_name",
        "output_dir",
        "started_at",
        "finished_at",
        "stage_statuses",
        "artifact_paths",
        "failures",
    }
    assert initialized["sample_id"] == "sample-001"
    assert initialized["config_name"] == "config_gpt_5_4_mini.yaml"
    assert manifest_path.exists()
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk["stage_statuses"] == {}
    assert on_disk["artifact_paths"] == {}
    assert on_disk["failures"] == []


def test_update_run_manifest_tracks_stage_status_and_artifacts(tmp_path: Path) -> None:
    """update_run_manifest stores stage status and artifact paths."""

    manifest_path = tmp_path / "run_manifest.json"
    initialize_run_manifest(
        manifest_path,
        "sample-001",
        "config_gpt_5_4_mini.yaml",
        tmp_path / "outputs" / "sample_sample-001",
    )

    updated = update_run_manifest(
        manifest_path,
        stage_name="generate_original_code",
        status="passed",
        artifact_paths={"original_code_path": "outputs/sample_sample-001/01_original/original_code.py"},
    )

    on_disk = load_run_manifest(manifest_path)
    assert updated["stage_statuses"]["generate_original_code"] == "passed"
    assert on_disk["artifact_paths"]["original_code_path"] == "outputs/sample_sample-001/01_original/original_code.py"
    assert on_disk["stage_statuses"]["generate_original_code"] == "passed"


def test_append_run_failure_and_finalize_manifest(tmp_path: Path) -> None:
    """append_run_failure records a readable failure and finalize_run_manifest sets finished_at."""

    manifest_path = tmp_path / "run_manifest.json"
    initialize_run_manifest(
        manifest_path,
        "sample-001",
        "config_gpt_5_4_mini.yaml",
        tmp_path / "outputs" / "sample_sample-001",
    )
    append_run_failure(
        manifest_path,
        stage_name="generate_fea_ready_code",
        message="parse error",
        artifact_paths={"fea_ready_failure_path": "outputs/sample_sample-001/02_fea_ready/fea_ready_failure.txt"},
    )
    finalized = finalize_run_manifest(manifest_path)

    assert finalized["finished_at"] is not None
    assert finalized["failures"]
    assert finalized["failures"][0]["message"] == "parse error"


def test_update_run_manifest_rejects_invalid_status(tmp_path: Path) -> None:
    """update_run_manifest rejects statuses outside the allowed set."""

    manifest_path = tmp_path / "run_manifest.json"
    initialize_run_manifest(
        manifest_path,
        "sample-001",
        "config_gpt_5_4_mini.yaml",
        tmp_path / "outputs" / "sample_sample-001",
    )

    with pytest.raises(ValueError, match="Invalid run manifest status"):
        update_run_manifest(manifest_path, stage_name="render_views", status="done")

    assert RUN_MANIFEST_ALLOWED_STATUSES == ("pending", "running", "passed", "failed", "skipped")
