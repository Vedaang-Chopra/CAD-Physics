"""Schema definitions for FEA load cases, selector hints, and manual reports."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LoadCase:
    """Structured manual-FEA load case for one sample."""

    sample_id: str
    units: str
    material: dict[str, Any]
    boundary_conditions: list[dict[str, Any]]
    loads: list[dict[str, Any]]
    requirements: dict[str, Any]


@dataclass(slots=True)
class SelectorHints:
    """Human-confirmable support and load selector hints for State B."""

    sample_id: str
    fixed_region_description: str
    load_region_description: str
    fixed_region_selector: dict[str, Any]
    load_region_selector: dict[str, Any]
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RevisionChangeLog:
    """Machine-readable summary of a code revision."""

    sample_id: str
    source_state: str
    target_state: str
    preserve_identity: bool
    changed_features: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ManualFEAReport:
    """Manual FreeCAD and CalculiX result template for one sample."""

    sample_id: str
    solver: str
    manual_run: bool
    max_von_mises_pa: float | None
    max_displacement_mm: float | None
    yield_strength_pa: float
    required_safety_factor: float
    computed_safety_factor: float | None
    passes_stress: bool | None
    passes_displacement: bool | None
    overall_pass: bool | None
    stress_hotspot_description: str
    notes: list[str]
