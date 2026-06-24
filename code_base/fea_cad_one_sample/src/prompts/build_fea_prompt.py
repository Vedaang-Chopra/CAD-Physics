"""Build the FEA-ready prompt for a single CAD sample."""

from __future__ import annotations

import logging
from typing import Any

from src.prompts.prompt_templates import (
    FEA_PROMPT_CORE_INSTRUCTIONS,
    FEA_PROMPT_HEADER,
    FEA_PROMPT_REQUIREMENT_LABELS,
    FEA_PROMPT_REQUIREMENT_TEXT,
)
from src.schemas.fea import LoadCase
from src.schemas.sample import CADSample

logger = logging.getLogger(__name__)


def build_fea_prompt(sample: CADSample, load_case: LoadCase) -> str:
    """Build an FEA-ready prompt from a CAD sample and load case."""

    logger.info(
        "build_fea_prompt | start | sample_id=%s | prompt_variant=%s",
        sample.sample_id,
        sample.prompt_variant,
    )
    try:
        prompt = _render_prompt(sample, load_case)
        logger.info(
            "build_fea_prompt | done | sample_id=%s | line_count=%d",
            sample.sample_id,
            len(prompt.splitlines()),
        )
        return prompt
    except Exception:
        logger.exception(
            "build_fea_prompt | failed | sample_id=%s | prompt_variant=%s",
            sample.sample_id,
            sample.prompt_variant,
        )
        raise


def _render_prompt(sample: CADSample, load_case: LoadCase) -> str:
    """Render the prompt body using the sample prompt and load-case defaults."""

    material = load_case.material
    requirements = load_case.requirements
    fixed_support_region = _format_region(load_case.boundary_conditions, "fixed/support region")
    load_region = _format_region(load_case.loads, "load region")
    force_description = _format_force(load_case.loads)
    direction_description = _format_direction(load_case.loads)

    return (
        f"{FEA_PROMPT_HEADER}\n\n"
        f"Original design prompt:\n{sample.prompt.strip()}\n\n"
        f"Sample ID: {sample.sample_id}\n"
        f"Prompt variant: {sample.prompt_variant}\n\n"
        "FEA context:\n"
        f"- material: {material.get('name', 'Unknown material')}\n"
        f"- Young's modulus: {material.get('youngs_modulus_pa')} Pa\n"
        f"- Poisson's ratio: {material.get('poissons_ratio')}\n"
        f"- yield strength: {material.get('yield_strength_pa')} Pa\n"
        f"- fixed/support region: {fixed_support_region}\n"
        f"- load region: {load_region}\n"
        f"- force magnitude and direction: {force_description}; direction {direction_description}\n"
        f"- max displacement: {requirements.get('max_displacement_mm')} mm\n"
        f"- safety factor: {requirements.get('required_safety_factor')}\n"
        f"- target max von Mises stress: {requirements.get('max_von_mises_pa')} Pa\n"
        f"- meshability: {FEA_PROMPT_REQUIREMENT_TEXT[0]}\n"
        f"- STEP export: {FEA_PROMPT_REQUIREMENT_TEXT[1]}\n"
        f"- single connected solid: {FEA_PROMPT_REQUIREMENT_TEXT[2]}\n\n"
        "Required prompt content checklist:\n"
        + "\n".join(f"- {item}" for item in FEA_PROMPT_REQUIREMENT_LABELS)
        + "\n\n"
        "Instructions:\n"
        + "\n".join(FEA_PROMPT_CORE_INSTRUCTIONS)
        + "\n\n"
        "Return only CadQuery Python code."
    )


def _format_region(items: list[dict[str, Any]], label: str) -> str:
    """Format a boundary-condition or load region description."""

    if not items:
        return f"Unspecified {label}"

    first_item = items[0]
    description = str(first_item.get("description") or f"Unspecified {label}").strip()
    selector = first_item.get("selector")
    if selector is None:
        return f"{description} (selector: null)"
    return f"{description} (selector: {selector})"


def _format_force(loads: list[dict[str, Any]]) -> str:
    """Format the force magnitude summary for the first force load."""

    if not loads:
        return "0 N"

    first_load = loads[0]
    magnitude = first_load.get("magnitude_n")
    return f"{magnitude} N"


def _format_direction(loads: list[dict[str, Any]]) -> str:
    """Format the force direction for the first load."""

    if not loads:
        return "[]"

    first_load = loads[0]
    direction = first_load.get("direction")
    return str(direction)
