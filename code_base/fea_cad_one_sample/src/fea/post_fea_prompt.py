"""Write the post-FEA refinement prompt and comparison template."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.reports.build_comparison_report import build_post_fea_comparison_report
from src.schemas.fea import LoadCase

logger = logging.getLogger(__name__)


def write_post_fea_prompt(
    sample_id: str,
    load_case: LoadCase,
    report_path: Path,
    output_dir: Path,
    force: bool = False,
) -> dict[str, str]:
    """Write the post-FEA feedback prompt and comparison template."""

    logger.info(
        "write_post_fea_prompt | start | sample_id=%s | report_path=%s | output_dir=%s | force=%s",
        sample_id,
        report_path,
        output_dir,
        force,
    )
    try:
        output_dir = Path(output_dir)
        report_path = Path(report_path)
        prompt_path = output_dir / "fea_feedback_prompt.txt"
        comparison_path = output_dir / "comparison_after_fea.md"
        _ensure_can_write(prompt_path, comparison_path, force=force)
        output_dir.mkdir(parents=True, exist_ok=True)

        report = _load_manual_report(report_path)
        prompt_path.write_text(_render_post_fea_prompt(sample_id, load_case, report), encoding="utf-8")
        comparison_written_path = build_post_fea_comparison_report(
            sample_id=sample_id,
            load_case=load_case,
            report=report,
            output_dir=output_dir,
            force=force,
        )
        result = {
            "fea_feedback_prompt_path": str(prompt_path),
            "comparison_after_fea_path": str(comparison_written_path),
        }
        logger.info(
            "write_post_fea_prompt | done | sample_id=%s | files=%s",
            sample_id,
            sorted(result.keys()),
        )
        return result
    except Exception:
        logger.exception(
            "write_post_fea_prompt | failed | sample_id=%s | report_path=%s | output_dir=%s",
            sample_id,
            report_path,
            output_dir,
        )
        raise


def _ensure_can_write(prompt_path: Path, comparison_path: Path, *, force: bool) -> None:
    """Refuse to overwrite the post-FEA artifacts unless force is enabled."""

    if force:
        return
    if prompt_path.exists() or comparison_path.exists():
        raise FileExistsError(
            f"Existing post-FEA artifacts found in {prompt_path.parent}. Use force=True to overwrite."
        )


def _load_manual_report(report_path: Path) -> dict[str, Any]:
    """Load the manual FreeCAD FEM report JSON from disk."""

    if not report_path.exists():
        raise FileNotFoundError(f"Manual FEA report not found: {report_path}")
    return json.loads(report_path.read_text(encoding="utf-8"))


def _render_post_fea_prompt(sample_id: str, load_case: LoadCase, report: dict[str, Any]) -> str:
    """Render the post-FEA refinement prompt."""

    max_von_mises_pa = _format_value(report, "max_von_mises_pa")
    max_displacement_mm = _format_value(report, "max_displacement_mm")
    computed_safety_factor = _format_value(report, "computed_safety_factor")
    stress_hotspot_description = _format_value(report, "stress_hotspot_description")
    overall_pass = _format_value(report, "overall_pass")

    return "\n".join(
        [
            "The CAD design was tested using FreeCAD FEM + CalculiX.",
            "",
            f"Sample ID: {sample_id}",
            "",
            "Load case:",
            f"- Material: {load_case.material.get('name', 'Unknown material')}",
            f"- Young's modulus: {load_case.material.get('youngs_modulus_pa')} Pa",
            f"- Poisson's ratio: {load_case.material.get('poissons_ratio')}",
            f"- Yield strength: {load_case.material.get('yield_strength_pa')} Pa",
            f"- Fixed/support region: {_format_region(load_case.boundary_conditions, default='fixed/support region')}",
            f"- Load region: {_format_region(load_case.loads, default='load region')}",
            f"- Force magnitude and direction: {_format_force(load_case.loads)} {_format_direction(load_case.loads)}".strip(),
            f"- Max displacement target: {load_case.requirements.get('max_displacement_mm')} mm",
            f"- Required safety factor: {load_case.requirements.get('required_safety_factor')}",
            f"- Max von Mises target: {load_case.requirements.get('max_von_mises_pa')} Pa",
            "",
            "FEA result:",
            f"- Max von Mises stress: {max_von_mises_pa}",
            f"- Max displacement: {max_displacement_mm}",
            f"- Computed safety factor: {computed_safety_factor}",
            f"- Stress hotspot: {stress_hotspot_description}",
            f"- Pass/fail: {overall_pass}",
            "",
            "Revise the CadQuery design.",
            "Keep the original design intent.",
            "Do not change the material or load.",
            "Improve stress and displacement performance.",
            "Prefer simple meshable geometry.",
            "Use one connected solid.",
            "Preserve clear fixed and load regions.",
            "Export STEP.",
            "",
            "If stress too high:",
            "- add gussets/ribs,",
            "- increase thickness,",
            "- add fillets near the hotspot,",
            "- improve load path.",
            "",
            "If displacement too high:",
            "- increase section height,",
            "- add triangular support,",
            "- shorten unsupported span if allowed,",
            "- add stiffening rib.",
            "",
            "If overbuilt:",
            "- reduce unnecessary bulk,",
            "- add cutouts away from stress paths,",
            "- keep safety factor above requirement.",
            "",
        ]
    )


def _format_value(report: dict[str, Any], key: str) -> Any:
    """Format a manual FEA report value or return a placeholder."""

    value = report.get(key)
    if value in (None, ""):
        return "<pending>"
    return value


def _format_region(items: list[dict[str, Any]], default: str) -> str:
    """Format the first region description from a load-case list."""

    if not items:
        return default
    first_item = items[0]
    description = str(first_item.get("description") or default).strip()
    selector = first_item.get("selector")
    if selector is None:
        return description
    return f"{description} (selector: {selector})"


def _format_force(loads: list[dict[str, Any]]) -> str:
    """Format the first applied load magnitude."""

    if not loads:
        return "200 N"
    magnitude = loads[0].get("magnitude_n", 200)
    return f"{magnitude} N"


def _format_direction(loads: list[dict[str, Any]]) -> str:
    """Format the first applied load direction."""

    if not loads:
        return "downward"
    return str(loads[0].get("direction", "downward"))
