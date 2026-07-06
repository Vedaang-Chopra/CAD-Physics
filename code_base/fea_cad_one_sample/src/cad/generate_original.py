"""Persist the database-original CadQuery sample for State A."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from src.schemas.config import PipelineConfig
from src.schemas.sample import CADSample

logger = logging.getLogger(__name__)


def generate_original_code(sample: CADSample, config: PipelineConfig) -> str:
    """Persist the DB-original prompt/code artifacts and return the code."""

    logger.info(
        "generate_original_code | start | sample_id=%s | config_name=%s",
        sample.sample_id,
        config.config_name,
    )
    try:
        code = _require_ground_truth_code(sample)
        artifact_dir = _artifact_dir(sample, config)
        _ensure_original_artifacts_can_be_written(artifact_dir, force=config.force)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        prompt_path = artifact_dir / "original_prompt.txt"
        code_path = artifact_dir / "database_original_code.py"
        metadata_path = artifact_dir / "metadata.json"
        provenance_path = artifact_dir / "provenance.json"

        _write_text(prompt_path, sample.prompt)
        _write_text(code_path, code)
        code_hash = _sha256_text(code)

        metadata = {
            "sample_id": sample.sample_id,
            "prompt_variant": sample.prompt_variant,
            "source": sample.source,
            "selection_mode": sample.metadata.get("selection_mode"),
            "original_prompt_path": str(prompt_path),
            "database_original_code_path": str(code_path),
            "code_hash_sha256": code_hash,
        }
        provenance = {
            "sample_id": sample.sample_id,
            "source": sample.source,
            "prompt_source": "database",
            "prompt_path": str(prompt_path),
            "code_path": str(code_path),
            "code_hash_sha256": code_hash,
            "prompt_sha256": _sha256_text(sample.prompt),
            "code_line_count": len(code.splitlines()),
        }

        _write_json(metadata_path, metadata)
        _write_json(provenance_path, provenance)
        logger.info(
            "generate_original_code | done | sample_id=%s | artifact_dir=%s | code_hash=%s",
            sample.sample_id,
            artifact_dir,
            code_hash,
        )
        return code
    except Exception:
        logger.exception(
            "generate_original_code | failed | sample_id=%s | config_name=%s",
            sample.sample_id,
            config.config_name,
        )
        raise


def _artifact_dir(sample: CADSample, config: PipelineConfig) -> Path:
    """Return the canonical State A artifact directory for one sample."""

    return Path(config.output_root) / f"sample_{sample.sample_id}" / "01_dataset_original"


def _ensure_original_artifacts_can_be_written(artifact_dir: Path, *, force: bool) -> None:
    """Refuse to overwrite State A artifacts unless force is enabled."""

    if force:
        return
    existing_paths = [
        artifact_dir / "original_prompt.txt",
        artifact_dir / "database_original_code.py",
        artifact_dir / "metadata.json",
        artifact_dir / "provenance.json",
    ]
    if any(path.exists() for path in existing_paths):
        raise FileExistsError(
            f"Existing original artifacts found in {artifact_dir}. Use force=True to overwrite."
        )


def _require_ground_truth_code(sample: CADSample) -> str:
    """Return the exact DB original code or raise a clear error."""

    code = sample.ground_truth_code
    if not isinstance(code, str) or not code.strip():
        raise LookupError(f"Sample {sample.sample_id} does not contain original CAD code.")
    return code


def _write_text(path: Path, text: str) -> None:
    """Write text without newline translation."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a compact JSON artifact with a trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_text(text: str) -> str:
    """Return the SHA-256 hash for a text payload."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
