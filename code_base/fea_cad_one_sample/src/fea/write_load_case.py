"""Write the structured load case JSON for the one-sample FEA workflow."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from src.schemas.fea import LoadCase, SelectorHints

logger = logging.getLogger(__name__)

MATERIAL_NAME = "Aluminum 6061-T6"
YOUNGS_MODULUS_PA = 68_900_000_000
POISSONS_RATIO = 0.33
YIELD_STRENGTH_PA = 276_000_000
LOAD_N = 200
LOAD_DIRECTION = [0, 0, -1]
MAX_DISPLACEMENT_MM = 1.0
REQUIRED_SAFETY_FACTOR = 2.0
MAX_VON_MISES_PA = int(YIELD_STRENGTH_PA / REQUIRED_SAFETY_FACTOR)
DEFAULT_FIXED_REGION_DESCRIPTION = "wall-facing mounting plate face"
DEFAULT_LOAD_REGION_DESCRIPTION = "top face near free end"
DEFAULT_FIXED_REGION_SELECTOR = {"axis": "x", "side": "minimum"}
DEFAULT_LOAD_REGION_SELECTOR = {"axis": "x", "side": "maximum"}


def write_load_case(sample_id: str, output_path: Path, force: bool = False) -> LoadCase:
    """Write the default FEA load case JSON for one sample."""

    logger.info(
        "write_load_case | start | sample_id=%s | output_path=%s | force=%s",
        sample_id,
        output_path,
        force,
    )
    try:
        output_path = Path(output_path)
        _ensure_can_write(output_path, force=force)
        load_case = LoadCase(
            sample_id=sample_id,
            units="mm",
            material={
                "name": MATERIAL_NAME,
                "youngs_modulus_pa": YOUNGS_MODULUS_PA,
                "poissons_ratio": POISSONS_RATIO,
                "yield_strength_pa": YIELD_STRENGTH_PA,
            },
            boundary_conditions=[
                {
                    "id": "fixed_region",
                    "type": "fixed_displacement",
                    "description": "User-defined or model-inferred fixed support region",
                    "selector": None,
                }
            ],
            loads=[
                {
                    "id": "load_region",
                    "type": "force",
                    "magnitude_n": LOAD_N,
                    "direction": list(LOAD_DIRECTION),
                    "description": "User-defined or model-inferred load application region",
                    "selector": None,
                }
            ],
            requirements={
                "max_displacement_mm": MAX_DISPLACEMENT_MM,
                "required_safety_factor": REQUIRED_SAFETY_FACTOR,
                "max_von_mises_pa": MAX_VON_MISES_PA,
            },
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(asdict(load_case), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        logger.info(
            "write_load_case | done | sample_id=%s | output_path=%s | max_von_mises_pa=%s",
            sample_id,
            output_path,
            MAX_VON_MISES_PA,
        )
        return load_case
    except Exception:
        logger.exception(
            "write_load_case | failed | sample_id=%s | output_path=%s | force=%s",
            sample_id,
            output_path,
            force,
        )
        raise


def write_selector_hints(load_case: LoadCase, output_path: Path, force: bool = False) -> SelectorHints:
    """Write the State B selector-hints JSON for one sample."""

    logger.info(
        "write_selector_hints | start | sample_id=%s | output_path=%s | force=%s",
        load_case.sample_id,
        output_path,
        force,
    )
    try:
        output_path = Path(output_path)
        _ensure_can_write(output_path, force=force)
        hints = _build_selector_hints(load_case)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(asdict(hints), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        logger.info(
            "write_selector_hints | done | sample_id=%s | output_path=%s",
            load_case.sample_id,
            output_path,
        )
        return hints
    except Exception:
        logger.exception(
            "write_selector_hints | failed | sample_id=%s | output_path=%s | force=%s",
            load_case.sample_id,
            output_path,
            force,
        )
        raise


def _build_selector_hints(load_case: LoadCase) -> SelectorHints:
    """Build default selector hints from the load case."""

    fixed_region = _first_region(
        load_case.boundary_conditions,
        DEFAULT_FIXED_REGION_DESCRIPTION,
        DEFAULT_FIXED_REGION_SELECTOR,
    )
    load_region = _first_region(
        load_case.loads,
        DEFAULT_LOAD_REGION_DESCRIPTION,
        DEFAULT_LOAD_REGION_SELECTOR,
    )
    notes = [
        "Confirm the fixed region before running FreeCAD FEM.",
        "Confirm the load region before running FreeCAD FEM.",
    ]
    return SelectorHints(
        sample_id=load_case.sample_id,
        fixed_region_description=str(fixed_region["description"]),
        load_region_description=str(load_region["description"]),
        fixed_region_selector=dict(fixed_region["selector"]),
        load_region_selector=dict(load_region["selector"]),
        notes=notes,
    )


def _first_region(
    entries: list[dict[str, Any]],
    default_description: str,
    default_selector: Mapping[str, Any],
) -> dict[str, Any]:
    """Extract a region description and selector or fall back to defaults."""

    if not entries:
        return {"description": default_description, "selector": dict(default_selector)}

    first_item = entries[0]
    selector = first_item.get("selector")
    if selector is None:
        return {"description": default_description, "selector": dict(default_selector)}

    description = str(first_item.get("description") or default_description).strip() or default_description
    return {"description": description, "selector": selector}


def _ensure_can_write(output_path: Path, *, force: bool) -> None:
    """Refuse to overwrite the load-case JSON unless force is enabled."""

    if force:
        return
    if output_path.exists():
        raise FileExistsError(f"Existing load case found at {output_path}. Use force=True to overwrite.")
