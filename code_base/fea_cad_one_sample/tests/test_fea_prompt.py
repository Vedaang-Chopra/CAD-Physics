"""Unit tests for the FEA prompt builder."""

from __future__ import annotations

from src.prompts.build_fea_prompt import build_fea_prompt
from src.schemas.fea import LoadCase
from src.schemas.sample import CADSample


def test_build_fea_prompt_includes_required_content() -> None:
    """build_fea_prompt includes all required FEA prompt terms."""

    sample = CADSample(
        sample_id="sample-001",
        prompt="Design a simple bracket with a clear support face.",
        prompt_variant="expert",
        source="cadcodeverify-db",
        metadata={},
    )
    load_case = LoadCase(
        sample_id="sample-001",
        units="mm",
        material={
            "name": "Aluminum 6061-T6",
            "youngs_modulus_pa": 68_900_000_000,
            "poissons_ratio": 0.33,
            "yield_strength_pa": 276_000_000,
        },
        boundary_conditions=[
            {
                "id": "fixed_region",
                "type": "fixed_displacement",
                "description": "Fixed support on the base face",
                "selector": None,
            }
        ],
        loads=[
            {
                "id": "load_region",
                "type": "force",
                "magnitude_n": 200,
                "direction": [0, 0, -1],
                "description": "Downward force on the top face",
                "selector": None,
            }
        ],
        requirements={
            "max_displacement_mm": 1.0,
            "required_safety_factor": 2.0,
            "max_von_mises_pa": 138_000_000,
        },
    )

    prompt = build_fea_prompt(sample, load_case)

    required_phrases = [
        "material",
        "Young's modulus",
        "Poisson's ratio",
        "yield strength",
        "fixed/support region",
        "load region",
        "force magnitude and direction",
        "max displacement",
        "safety factor",
        "meshability",
        "STEP export",
        "single connected solid",
        "Preserve the original design intent.",
        "Make the geometry suitable for FEA.",
        "Use a single connected solid.",
        "Avoid tiny decorative features.",
        "Use clear flat support and load regions.",
        "Export STEP.",
        "Prefer simple mechanical structure.",
        "Design a simple bracket with a clear support face.",
        "Aluminum 6061-T6",
        "138000000",
    ]

    for phrase in required_phrases:
        assert phrase in prompt
