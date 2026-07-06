"""Write the manual FreeCAD FEM report template."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from src.fea.freecad_manual_instructions import SCREENSHOT_FILENAMES
from src.schemas.fea import ManualFEAReport

logger = logging.getLogger(__name__)

MANUAL_SOLVER_NAME = "FreeCAD FEM + CalculiX"
DEFAULT_YIELD_STRENGTH_PA = 276_000_000
DEFAULT_REQUIRED_SAFETY_FACTOR = 2.0


def write_manual_fea_report_template(
    sample_id: str,
    output_path: Path,
    force: bool = False,
) -> ManualFEAReport:
    """Write the template report JSON for manual FreeCAD FEM results."""

    logger.info(
        "write_manual_fea_report_template | start | sample_id=%s | output_path=%s | force=%s",
        sample_id,
        output_path,
        force,
    )
    try:
        output_path = Path(output_path)
        _ensure_can_write(output_path, force=force)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report = _build_template(sample_id)
        output_path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        logger.info(
            "write_manual_fea_report_template | done | sample_id=%s | output_path=%s",
            sample_id,
            output_path,
        )
        return report
    except Exception:
        logger.exception(
            "write_manual_fea_report_template | failed | sample_id=%s | output_path=%s",
            sample_id,
            output_path,
        )
        raise


def _build_template(sample_id: str) -> ManualFEAReport:
    """Build the blank manual FEA report template dataclass."""

    return ManualFEAReport(
        sample_id=sample_id,
        solver=MANUAL_SOLVER_NAME,
        manual_run=True,
        max_von_mises_pa=None,
        max_displacement_mm=None,
        yield_strength_pa=DEFAULT_YIELD_STRENGTH_PA,
        required_safety_factor=DEFAULT_REQUIRED_SAFETY_FACTOR,
        computed_safety_factor=None,
        passes_stress=None,
        passes_displacement=None,
        overall_pass=None,
        stress_hotspot_description="",
        notes=[],
    )


def validate_manual_fea_completion(
    report: Mapping[str, Any],
    evidence_paths: list[Path],
) -> dict[str, Any]:
    """Validate that manual FEA results are complete enough for State C."""

    missing_fields: list[str] = []
    for field_name in (
        "max_von_mises_pa",
        "max_displacement_mm",
        "computed_safety_factor",
        "passes_stress",
        "passes_displacement",
        "overall_pass",
    ):
        value = report.get(field_name)
        if value in (None, "", "<pending>"):
            missing_fields.append(field_name)

    stress_hotspot_description = str(report.get("stress_hotspot_description") or "").strip()
    if not stress_hotspot_description:
        missing_fields.append("stress_hotspot_description")

    missing_evidence_paths = [str(path) for path in evidence_paths if not Path(path).exists()]
    is_complete = not missing_fields and not missing_evidence_paths
    validation = {
        "is_complete": is_complete,
        "missing_fields": missing_fields,
        "missing_evidence_paths": missing_evidence_paths,
        "report": dict(report),
    }
    logger.info(
        "validate_manual_fea_completion | result | is_complete=%s | missing_fields=%s | missing_evidence_paths=%s",
        is_complete,
        missing_fields,
        missing_evidence_paths,
    )
    return validation


def required_manual_fea_evidence_paths(manual_dir: Path, screenshot_dir: Path | None = None) -> list[Path]:
    """Return the canonical screenshot/result paths expected for manual FEA."""

    manual_dir = Path(manual_dir)
    screenshot_dir = Path(screenshot_dir) if screenshot_dir is not None else manual_dir / "screenshots"
    return [screenshot_dir / name for name in SCREENSHOT_FILENAMES]


def _ensure_can_write(output_path: Path, *, force: bool) -> None:
    """Refuse to overwrite the report template unless force is enabled."""

    if force:
        return
    if output_path.exists():
        raise FileExistsError(f"Existing manual FEA report template found at {output_path}. Use force=True to overwrite.")
