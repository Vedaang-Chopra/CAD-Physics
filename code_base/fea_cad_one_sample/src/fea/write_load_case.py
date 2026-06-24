"""Write the structured load case JSON for the one-sample FEA workflow."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from src.schemas.fea import LoadCase

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


def write_load_case(sample_id: str, output_path: Path) -> LoadCase:
    """Write the default FEA load case JSON for one sample."""

    logger.info(
        "write_load_case | start | sample_id=%s | output_path=%s",
        sample_id,
        output_path,
    )
    try:
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
            "write_load_case | failed | sample_id=%s | output_path=%s",
            sample_id,
            output_path,
        )
        raise
