"""Reusable template fragments for FEA prompt construction."""

from __future__ import annotations

FEA_PROMPT_HEADER = "Generate FEA-ready CadQuery code."
FEA_PROMPT_CORE_INSTRUCTIONS = (
    "Preserve the original design intent.",
    "Make the geometry suitable for FEA.",
    "Use a single connected solid.",
    "Avoid tiny decorative features.",
    "Use clear flat support and load regions.",
    "Export STEP.",
    "Prefer simple mechanical structure.",
)
FEA_PROMPT_REQUIREMENT_LABELS = (
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
)
FEA_PROMPT_REQUIREMENT_TEXT = (
    "Meshability requirements: keep the geometry simple enough to mesh cleanly with common FEA tools.",
    "STEP export requirement: export the final solid as STEP.",
    "Single connected solid requirement: keep the final model as one connected solid body.",
)
