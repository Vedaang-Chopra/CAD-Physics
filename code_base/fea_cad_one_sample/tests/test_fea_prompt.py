"""Unit tests for the FEA prompt builder."""

from __future__ import annotations

from src.prompts.build_fea_prompt import build_fea_prompt
from src.schemas.fea import LoadCase, SelectorHints


def test_build_fea_prompt_includes_required_content() -> None:
    """build_fea_prompt includes the State A prompt, code, and revision rules."""

    original_prompt = "Design a simple bracket with a clear support face."
    original_code = "import cadquery as cq\nresult = cq.Workplane().box(20, 10, 5)"
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
    selector_hints = SelectorHints(
        sample_id="sample-001",
        fixed_region_description="wall-facing mounting plate face",
        load_region_description="top face near free end",
        fixed_region_selector={"axis": "x", "side": "minimum"},
        load_region_selector={"axis": "x", "side": "maximum"},
    )

    prompt = build_fea_prompt(original_prompt, original_code, load_case, selector_hints)

    required_phrases = [
        "Revise the original DB CadQuery design with FEA constraints.",
        "State A original prompt:",
        original_prompt,
        "State A original DB code:",
        original_code,
        "Load case (JSON):",
        "Selector hints (JSON):",
        "preserve identity",
        "permitted modifications",
        "machine-readable change log",
        "Preserve the original design identity.",
        "Revise State A instead of designing an unrelated part.",
        "Use only permitted modifications such as thickness changes, ribs, gussets, fillets, local strengthening, and support/load face cleanup.",
        "Return a machine-readable change_log object.",
        "Return only JSON containing code_lines and change_log.",
        "Aluminum 6061-T6",
        "138000000",
    ]

    for phrase in required_phrases:
        assert phrase in prompt


def test_build_fea_prompt_rejects_empty_original_prompt() -> None:
    """build_fea_prompt raises ValueError when the original prompt is empty."""

    load_case = LoadCase(
        sample_id="sample-001",
        units="mm",
        material={"name": "Aluminum 6061-T6"},
        boundary_conditions=[],
        loads=[],
        requirements={},
    )
    selector_hints = SelectorHints(
        sample_id="sample-001",
        fixed_region_description="wall-facing mounting plate face",
        load_region_description="top face near free end",
        fixed_region_selector={"axis": "x", "side": "minimum"},
        load_region_selector={"axis": "x", "side": "maximum"},
    )

    try:
        build_fea_prompt("", "import cadquery as cq\nresult = cq.Workplane()", load_case, selector_hints)
    except ValueError as exc:
        assert "original_prompt" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty original prompt")
