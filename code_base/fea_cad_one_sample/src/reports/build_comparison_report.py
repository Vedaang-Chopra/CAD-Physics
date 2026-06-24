"""Build markdown comparison artifacts for original, FEA-ready, and post-FEA workflows."""

from __future__ import annotations

import difflib
import logging
from pathlib import Path
from typing import Any, Mapping

from src.schemas.fea import LoadCase

logger = logging.getLogger(__name__)


def build_comparison_artifacts(
    original_prompt: str,
    fea_prompt: str,
    output_dir: Path,
    notes: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, str]:
    """Write prompt and geometry comparison markdown files."""

    logger.info(
        "build_comparison_artifacts | start | output_dir=%s | force=%s | notes_keys=%s",
        output_dir,
        force,
        sorted((notes or {}).keys()),
    )
    try:
        output_dir = Path(output_dir)
        prompt_diff_path = output_dir / "prompt_diff.md"
        geometry_notes_path = output_dir / "geometry_diff_notes.md"
        _ensure_can_write_comparison(prompt_diff_path, geometry_notes_path, force=force)
        output_dir.mkdir(parents=True, exist_ok=True)

        prompt_diff_path.write_text(_render_prompt_diff(original_prompt, fea_prompt), encoding="utf-8")
        geometry_notes_path.write_text(_render_geometry_notes(notes), encoding="utf-8")
        result = {
            "prompt_diff": str(prompt_diff_path),
            "geometry_diff_notes": str(geometry_notes_path),
        }
        logger.info(
            "build_comparison_artifacts | done | output_dir=%s | files=%s",
            output_dir,
            sorted(result.keys()),
        )
        return result
    except Exception:
        logger.exception(
            "build_comparison_artifacts | failed | output_dir=%s | force=%s",
            output_dir,
            force,
        )
        raise


def build_post_fea_comparison_report(
    sample_id: str,
    load_case: LoadCase,
    report: Mapping[str, Any],
    output_dir: Path,
    force: bool = False,
) -> Path:
    """Write the post-FEA comparison markdown template."""

    logger.info(
        "build_post_fea_comparison_report | start | sample_id=%s | output_dir=%s | force=%s",
        sample_id,
        output_dir,
        force,
    )
    try:
        output_dir = Path(output_dir)
        output_path = output_dir / "comparison_after_fea.md"
        _ensure_can_write_single(output_path, force=force)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            _render_post_fea_comparison_report(sample_id=sample_id, load_case=load_case, report=report),
            encoding="utf-8",
        )
        logger.info(
            "build_post_fea_comparison_report | done | sample_id=%s | output_path=%s",
            sample_id,
            output_path,
        )
        return output_path
    except Exception:
        logger.exception(
            "build_post_fea_comparison_report | failed | sample_id=%s | output_dir=%s | force=%s",
            sample_id,
            output_dir,
            force,
        )
        raise


def _ensure_can_write_comparison(prompt_diff_path: Path, geometry_notes_path: Path, *, force: bool) -> None:
    """Refuse to overwrite existing comparison markdown unless force is enabled."""

    if force:
        return
    if prompt_diff_path.exists() or geometry_notes_path.exists():
        raise FileExistsError(
            f"Existing comparison artifacts found in {prompt_diff_path.parent}. Use force=True to overwrite."
        )


def _ensure_can_write_single(output_path: Path, *, force: bool) -> None:
    """Refuse to overwrite a single markdown artifact unless force is enabled."""

    if force:
        return
    if output_path.exists():
        raise FileExistsError(f"Existing comparison report found at {output_path}. Use force=True to overwrite.")


def _render_prompt_diff(original_prompt: str, fea_prompt: str) -> str:
    """Render a unified diff between the original and FEA-ready prompts."""

    original_lines = (original_prompt or "").rstrip().splitlines()
    fea_lines = (fea_prompt or "").rstrip().splitlines()
    diff_lines = list(
        difflib.unified_diff(
            original_lines,
            fea_lines,
            fromfile="original_prompt.txt",
            tofile="fea_ready_prompt.txt",
            lineterm="",
        )
    )
    body = "\n".join(diff_lines) if diff_lines else "No textual differences."
    return "\n".join(
        [
            "# Prompt Diff",
            "",
            "## Original Prompt",
            "",
            original_prompt.strip() or "<empty>",
            "",
            "## FEA-Ready Prompt",
            "",
            fea_prompt.strip() or "<empty>",
            "",
            "## Unified Diff",
            "",
            body,
            "",
        ]
    )


def _render_geometry_notes(notes: dict[str, Any] | None) -> str:
    """Render geometry-comparison notes as markdown bullets."""

    notes = notes or {}
    lines = ["# Geometry Diff Notes", ""]
    if not notes:
        lines.append("- No notes provided.")
        lines.append("")
        return "\n".join(lines)

    for key in sorted(notes.keys()):
        value = notes[key]
        lines.append(f"- **{_format_note_key(key)}**: {_format_note_value(value)}")
    lines.append("")
    return "\n".join(lines)


def _render_post_fea_comparison_report(sample_id: str, load_case: LoadCase, report: Mapping[str, Any]) -> str:
    """Render the post-FEA comparison template markdown."""

    report_summary = _render_report_summary(report)
    load_case_summary = _render_load_case_summary(load_case)
    return "\n".join(
        [
            "# Post-FEA Comparison Template",
            "",
            f"Sample ID: {sample_id}",
            "",
            "## FEA Result Summary",
            "",
            report_summary,
            "",
            "## Load Case Summary",
            "",
            load_case_summary,
            "",
            "## Comparison Matrix",
            "",
            "| Aspect | Original CAD | FEA-ready CAD | Post-FEA refined CAD |",
            "|---|---|---|---|",
            "| Prompt differences | Baseline intent | Added FEA-aware constraints | TBD after refinement |",
            "| Code differences | Original CadQuery | FEA-ready CadQuery | TBD after refinement |",
            "| Visual differences | Original renders | FEA-ready renders | TBD after refinement |",
            "",
            "## What Changed Because of Physics Feedback",
            "",
            "- Use the FEA results above to decide whether to add ribs, increase thickness, add fillets, or improve the load path.",
            "- Keep the material and load case unchanged unless a later task explicitly updates the spec.",
            "- Preserve clear fixed and load regions so the geometry stays meshable.",
            "",
            "## Whether the Object Still Satisfies the Original Design Intent",
            "",
            "- Compare the refined CAD against the original prompt and the FEA-ready prompt.",
            "- Confirm the part still serves the same functional intent while reducing stress or displacement.",
            "- Mark the final state here after the refined model is generated.",
            "",
        ]
    )


def _render_report_summary(report: Mapping[str, Any]) -> str:
    """Render the manual FEA report summary section."""

    max_von_mises_pa = _format_report_value(report, "max_von_mises_pa")
    max_displacement_mm = _format_report_value(report, "max_displacement_mm")
    computed_safety_factor = _format_report_value(report, "computed_safety_factor")
    stress_hotspot_description = _format_report_value(report, "stress_hotspot_description")
    overall_pass = _format_report_value(report, "overall_pass")
    solver = str(report.get("solver") or "FreeCAD FEM + CalculiX").strip()
    lines = [
        f"- Solver: {solver}",
        f"- Max von Mises stress: {max_von_mises_pa} Pa",
        f"- Max displacement: {max_displacement_mm} mm",
        f"- Computed safety factor: {computed_safety_factor}",
        f"- Stress hotspot: {stress_hotspot_description}",
        f"- Pass/fail: {overall_pass}",
    ]
    return "\n".join(lines)


def _render_load_case_summary(load_case: LoadCase) -> str:
    """Render a concise summary of the load case used for manual FEA."""

    material = load_case.material
    requirements = load_case.requirements
    fixed_support = _format_region(load_case.boundary_conditions, default="fixed/support region")
    load_region = _format_region(load_case.loads, default="load region")
    force = _format_force(load_case.loads)
    direction = _format_direction(load_case.loads)
    return "\n".join(
        [
            f"- Material: {material.get('name', 'Unknown material')}",
            f"- Young's modulus: {material.get('youngs_modulus_pa')} Pa",
            f"- Poisson's ratio: {material.get('poissons_ratio')}",
            f"- Yield strength: {material.get('yield_strength_pa')} Pa",
            f"- Fixed/support region: {fixed_support}",
            f"- Load region: {load_region}",
            f"- Applied load: {force} {direction}".strip(),
            f"- Max displacement target: {requirements.get('max_displacement_mm')} mm",
            f"- Required safety factor: {requirements.get('required_safety_factor')}",
            f"- Max von Mises target: {requirements.get('max_von_mises_pa')} Pa",
        ]
    )


def _format_report_value(report: Mapping[str, Any], key: str) -> Any:
    """Format a manual FEA report value or return a placeholder."""

    value = report.get(key)
    if value in (None, ""):
        return "<pending>"
    return value


def _format_note_key(key: Any) -> str:
    """Format a note key for markdown output."""

    text = str(key).replace("_", " ").strip()
    return text[:1].upper() + text[1:] if text else "Note"


def _format_note_value(value: Any) -> str:
    """Format a note value for markdown output."""

    if isinstance(value, dict):
        nested = ", ".join(f"{_format_note_key(k)}={_format_note_value(v)}" for k, v in value.items())
        return nested or "{}"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_format_note_value(item) for item in value) or "[]"
    text = str(value).strip()
    return text or "-"


def _format_region(items: list[dict[str, Any]], default: str) -> str:
    """Format the first region description from a list of entries."""

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
    first_load = loads[0]
    magnitude = first_load.get("magnitude_n", 200)
    return f"{magnitude} N"


def _format_direction(loads: list[dict[str, Any]]) -> str:
    """Format the first applied load direction."""

    if not loads:
        return "downward"
    first_load = loads[0]
    direction = first_load.get("direction")
    return f"direction {direction}"
