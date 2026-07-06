"""Schema definitions for pipeline summaries and run manifest records."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

RUN_MANIFEST_ALLOWED_STATUSES: tuple[str, ...] = (
    "pending",
    "running",
    "passed",
    "failed",
    "blocked",
    "skipped",
)


@dataclass(slots=True)
class PipelineSummary:
    """High-level summary of one pipeline run."""

    sample_id: str
    output_dir: Path
    stage_statuses: dict[str, str]
    artifact_paths: dict[str, str]
    failures: list[dict[str, Any]]


@dataclass(slots=True)
class FEARevisionResult:
    """State B revision outputs and artifact paths."""

    sample_id: str
    prompt_path: Path
    load_case_path: Path
    selector_hints_path: Path
    code_path: Path
    change_log_path: Path
    provenance_path: Path
    step_path: Path
    stl_path: Path
    execution_log_path: Path
    view_paths: dict[str, Path]
    code_hash_sha256: str


@dataclass(slots=True)
class PostFEARevisionResult:
    """State C post-FEA revision outputs and artifact paths."""

    sample_id: str
    prompt_path: Path
    load_case_path: Path
    manual_report_path: Path
    screenshot_paths: list[Path]
    code_path: Path
    change_log_path: Path
    provenance_path: Path
    step_path: Path
    stl_path: Path
    execution_log_path: Path
    view_paths: dict[str, Path]
    code_hash_sha256: str


@dataclass(slots=True)
class RunManifestRecord:
    """Single stage record stored in run_manifest.json."""

    stage_name: str
    status: Literal["pending", "running", "passed", "failed", "skipped"]
    artifact_paths: dict[str, str]
    notes: list[str] | None = None
