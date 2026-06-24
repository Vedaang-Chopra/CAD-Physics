"""Run manifest helpers for the one-sample FEA pipeline."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.schemas.pipeline import RUN_MANIFEST_ALLOWED_STATUSES, RunManifestRecord

logger = logging.getLogger(__name__)


def create_run_manifest(sample_id: str, config_name: str, output_dir: Path) -> dict[str, Any]:
    """Create a fresh run-manifest payload."""

    logger.info(
        "create_run_manifest | start | sample_id=%s | config_name=%s | output_dir=%s",
        sample_id,
        config_name,
        output_dir,
    )
    try:
        manifest = {
            "sample_id": str(sample_id),
            "config_name": str(config_name),
            "output_dir": str(Path(output_dir)),
            "started_at": _now_iso(),
            "finished_at": None,
            "stage_statuses": {},
            "artifact_paths": {},
            "failures": [],
        }
        logger.info(
            "create_run_manifest | done | sample_id=%s | keys=%s",
            sample_id,
            sorted(manifest.keys()),
        )
        return manifest
    except Exception:
        logger.exception(
            "create_run_manifest | failed | sample_id=%s | config_name=%s | output_dir=%s",
            sample_id,
            config_name,
            output_dir,
        )
        raise


def initialize_run_manifest(manifest_path: Path, sample_id: str, config_name: str, output_dir: Path) -> dict[str, Any]:
    """Create and write an initial run manifest file."""

    logger.info(
        "initialize_run_manifest | start | manifest_path=%s | sample_id=%s",
        manifest_path,
        sample_id,
    )
    try:
        manifest = create_run_manifest(sample_id, config_name, output_dir)
        write_run_manifest(manifest_path, manifest)
        logger.info(
            "initialize_run_manifest | done | manifest_path=%s | sample_id=%s",
            manifest_path,
            sample_id,
        )
        return manifest
    except Exception:
        logger.exception(
            "initialize_run_manifest | failed | manifest_path=%s | sample_id=%s",
            manifest_path,
            sample_id,
        )
        raise


def load_run_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load a manifest JSON file from disk."""

    logger.info("load_run_manifest | start | manifest_path=%s", manifest_path)
    try:
        manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            raise FileNotFoundError(f"Run manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        logger.info(
            "load_run_manifest | done | manifest_path=%s | keys=%s",
            manifest_path,
            sorted(manifest.keys()),
        )
        return manifest
    except Exception:
        logger.exception("load_run_manifest | failed | manifest_path=%s", manifest_path)
        raise


def write_run_manifest(manifest_path: Path, manifest: Mapping[str, Any]) -> Path:
    """Write a run manifest payload to disk."""

    logger.info("write_run_manifest | start | manifest_path=%s", manifest_path)
    try:
        manifest_path = Path(manifest_path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        logger.info(
            "write_run_manifest | done | manifest_path=%s | keys=%s",
            manifest_path,
            sorted(manifest.keys()),
        )
        return manifest_path
    except Exception:
        logger.exception("write_run_manifest | failed | manifest_path=%s", manifest_path)
        raise


def update_run_manifest(
    manifest_path: Path,
    stage_name: str,
    status: str,
    artifact_paths: Mapping[str, str] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    """Update a manifest with one stage status and optional artifact paths."""

    logger.info(
        "update_run_manifest | start | manifest_path=%s | stage_name=%s | status=%s",
        manifest_path,
        stage_name,
        status,
    )
    try:
        if status not in RUN_MANIFEST_ALLOWED_STATUSES:
            raise ValueError(f"Invalid run manifest status: {status}")

        manifest = load_run_manifest(manifest_path)
        stage_record = RunManifestRecord(
            stage_name=stage_name,
            status=status,  # type: ignore[arg-type]
            artifact_paths=dict(artifact_paths or {}),
            notes=notes,
        )
        manifest.setdefault("stage_statuses", {})[stage_name] = status
        manifest.setdefault("artifact_paths", {}).update(dict(stage_record.artifact_paths))
        if notes:
            manifest.setdefault("failures", []).append(
                {
                    "stage_name": stage_name,
                    "status": status,
                    "notes": list(notes),
                    "artifact_paths": dict(stage_record.artifact_paths),
                }
            )
        write_run_manifest(manifest_path, manifest)
        logger.info(
            "update_run_manifest | done | manifest_path=%s | stage_name=%s | artifact_keys=%s",
            manifest_path,
            stage_name,
            sorted(stage_record.artifact_paths.keys()),
        )
        return manifest
    except Exception:
        logger.exception(
            "update_run_manifest | failed | manifest_path=%s | stage_name=%s | status=%s",
            manifest_path,
            stage_name,
            status,
        )
        raise


def append_run_failure(
    manifest_path: Path,
    stage_name: str,
    message: str,
    *,
    artifact_paths: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Append a readable failure entry to the run manifest."""

    logger.info(
        "append_run_failure | start | manifest_path=%s | stage_name=%s",
        manifest_path,
        stage_name,
    )
    try:
        manifest = load_run_manifest(manifest_path)
        failure = {
            "stage_name": stage_name,
            "message": message,
            "artifact_paths": dict(artifact_paths or {}),
            "timestamp": _now_iso(),
        }
        manifest.setdefault("failures", []).append(failure)
        write_run_manifest(manifest_path, manifest)
        logger.info(
            "append_run_failure | done | manifest_path=%s | stage_name=%s",
            manifest_path,
            stage_name,
        )
        return manifest
    except Exception:
        logger.exception(
            "append_run_failure | failed | manifest_path=%s | stage_name=%s",
            manifest_path,
            stage_name,
        )
        raise


def finalize_run_manifest(manifest_path: Path) -> dict[str, Any]:
    """Mark a run manifest as finished and persist it."""

    logger.info("finalize_run_manifest | start | manifest_path=%s", manifest_path)
    try:
        manifest = load_run_manifest(manifest_path)
        manifest["finished_at"] = _now_iso()
        write_run_manifest(manifest_path, manifest)
        logger.info("finalize_run_manifest | done | manifest_path=%s", manifest_path)
        return manifest
    except Exception:
        logger.exception("finalize_run_manifest | failed | manifest_path=%s", manifest_path)
        raise


def _now_iso() -> str:
    """Return a UTC ISO-8601 timestamp string."""

    return datetime.now(timezone.utc).isoformat()
