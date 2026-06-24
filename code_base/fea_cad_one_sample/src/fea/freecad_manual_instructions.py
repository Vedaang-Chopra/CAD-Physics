"""Write manual FreeCAD FEM instructions for the one-sample workflow."""

from __future__ import annotations

import logging
from pathlib import Path

from src.schemas.fea import LoadCase

logger = logging.getLogger(__name__)

FREECAD_SOLVER_NAME = "FreeCAD FEM + CalculiX"
SCREENSHOT_FILENAMES = (
    "mesh.png",
    "fixed_region.png",
    "load_region.png",
    "von_mises.png",
    "displacement.png",
)


def write_freecad_instructions(
    sample_id: str,
    step_path: Path,
    load_case: LoadCase,
    output_path: Path,
    force: bool = False,
) -> Path:
    """Write the manual FreeCAD FEM instructions markdown file."""

    logger.info(
        "write_freecad_instructions | start | sample_id=%s | step_path=%s | output_path=%s | force=%s",
        sample_id,
        step_path,
        output_path,
        force,
    )
    try:
        output_path = Path(output_path)
        step_path = Path(step_path)
        _ensure_can_write(output_path, force=force)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            _render_instructions(sample_id=sample_id, step_path=step_path, load_case=load_case),
            encoding="utf-8",
        )
        logger.info(
            "write_freecad_instructions | done | sample_id=%s | output_path=%s",
            sample_id,
            output_path,
        )
        return output_path
    except Exception:
        logger.exception(
            "write_freecad_instructions | failed | sample_id=%s | step_path=%s | output_path=%s",
            sample_id,
            step_path,
            output_path,
        )
        raise


def _ensure_can_write(output_path: Path, *, force: bool) -> None:
    """Refuse to overwrite the manual instruction file unless force is enabled."""

    if force:
        return
    if output_path.exists():
        raise FileExistsError(f"Existing manual FreeCAD instructions found at {output_path}. Use force=True to overwrite.")


def _render_instructions(sample_id: str, step_path: Path, load_case: LoadCase) -> str:
    """Render the manual FreeCAD FEM workflow instructions."""

    material = load_case.material
    requirements = load_case.requirements
    fixed_support = _format_first_region(load_case.boundary_conditions, default="fixed/support face")
    load_region = _format_first_region(load_case.loads, default="load face")
    load_description = _format_first_load(load_case.loads)
    load_direction = _format_first_direction(load_case.loads)

    return "\n".join(
        [
            "# Manual FreeCAD FEM Instructions",
            "",
            f"Sample ID: {sample_id}",
            f"STEP file: {step_path}",
            f"Solver: {FREECAD_SOLVER_NAME}",
            "",
            "## Load Case Summary",
            "",
            f"- Material: {material.get('name', 'Unknown material')}",
            f"- Young's modulus: {material.get('youngs_modulus_pa')} Pa",
            f"- Poisson's ratio: {material.get('poissons_ratio')}",
            f"- Yield strength: {material.get('yield_strength_pa')} Pa",
            f"- Fixed/support region: {fixed_support}",
            f"- Load region: {load_region}",
            f"- Applied load: {load_description} {load_direction}".strip(),
            f"- Max displacement target: {requirements.get('max_displacement_mm')} mm",
            f"- Required safety factor: {requirements.get('required_safety_factor')}",
            f"- Max von Mises target: {requirements.get('max_von_mises_pa')} Pa",
            "",
            "## Manual Steps",
            "",
            "1. Open FreeCAD.",
            f"2. Import {step_path.name}.",
            "3. Switch to the FEM workbench.",
            "4. Create a new analysis.",
            f"5. Assign material: {material.get('name', 'Aluminum 6061-T6')}.",
            f"6. Set Young's modulus, Poisson's ratio, and yield strength to the values above.",
            f"7. Add a fixed constraint to the {fixed_support}.",
            f"8. Add a force constraint: 200 N downward on the {load_region}.",
            "9. Create the mesh using Gmsh or Netgen.",
            "10. Run CalculiX manually.",
            "11. Open the results.",
            "12. Save screenshots for:",
            *[f"   - {name}" for name in SCREENSHOT_FILENAMES],
            "13. Record the following results:",
            "   - max von Mises stress",
            "   - max displacement",
            "   - solver success/failure",
            "   - visible stress hotspot location",
            "",
            "## macOS Note",
            "",
            "If FreeCAD does not find CalculiX automatically, set the CalculiX binary path in FreeCAD preferences.",
            "Do not require automated CalculiX execution in this prototype.",
            "",
        ]
    )


def _format_first_region(items: list[dict[str, object]], default: str) -> str:
    """Format the first region description from a list of load-case entries."""

    if not items:
        return default
    first_item = items[0]
    description = str(first_item.get("description") or default).strip()
    selector = first_item.get("selector")
    if selector is None:
        return description
    return f"{description} (selector: {selector})"


def _format_first_load(loads: list[dict[str, object]]) -> str:
    """Format the first applied load summary."""

    if not loads:
        return "200 N"
    first_load = loads[0]
    magnitude = first_load.get("magnitude_n", 200)
    return f"{magnitude} N"


def _format_first_direction(loads: list[dict[str, object]]) -> str:
    """Format the first applied load direction."""

    if not loads:
        return "downward"
    first_load = loads[0]
    direction = first_load.get("direction")
    return f"direction {direction}"
