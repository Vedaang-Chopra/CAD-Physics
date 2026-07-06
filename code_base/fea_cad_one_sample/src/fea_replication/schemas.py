"""Data contracts for the deterministic FEA replication pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class MaterialSpec:
    """Isotropic material definition used by the replication pipeline."""

    name: str
    youngs_modulus_pa: float
    poissons_ratio: float
    yield_strength_pa: float


@dataclass(slots=True)
class LoadSpec:
    """Concentrated load definition."""

    magnitude_n: float
    direction_vector: tuple[float, float, float]
    target_region: str
    target_node_set: str


@dataclass(slots=True)
class BoundaryConditionSpec:
    """Fixed support definition."""

    fixed_region: str
    fixed_node_set: str


@dataclass(slots=True)
class VerificationCriteria:
    """Pass/fail criteria for the replication run."""

    max_displacement_mm: float
    required_safety_factor: float


@dataclass(slots=True)
class GeometrySpec:
    """Geometry input specification."""

    source_step_path: Path | None = None
    placeholder_name: str = "cantilever_beam"
    length_mm: float = 120.0
    width_mm: float = 20.0
    thickness_mm: float = 10.0


@dataclass(slots=True)
class FEAReplicationConfig:
    """Complete analysis configuration for one deterministic study."""

    run_dir: Path
    job_name: str = "analysis"
    mesh_size_mm: float = 5.0
    geometry: GeometrySpec = field(default_factory=GeometrySpec)
    material: MaterialSpec = field(
        default_factory=lambda: MaterialSpec(
            name="Aluminum 6061",
            youngs_modulus_pa=69_000_000_000.0,
            poissons_ratio=0.33,
            yield_strength_pa=276_000_000.0,
        )
    )
    load: LoadSpec = field(
        default_factory=lambda: LoadSpec(
            magnitude_n=100.0,
            direction_vector=(0.0, 0.0, -1.0),
            target_region="free end face near max axis",
            target_node_set="LOAD_END",
        )
    )
    boundary_condition: BoundaryConditionSpec = field(
        default_factory=lambda: BoundaryConditionSpec(
            fixed_region="fixed end face near min axis",
            fixed_node_set="FIXED_END",
        )
    )
    verification_criteria: VerificationCriteria = field(
        default_factory=lambda: VerificationCriteria(
            max_displacement_mm=2.0,
            required_safety_factor=2.0,
        )
    )
    selection_margin_fraction: float = 0.08
    selection_margin_min_mm: float = 0.5
    solver_executable: str = "ccx"


@dataclass(slots=True)
class GeometrySummary:
    """Summary of the selected or generated geometry."""

    source_mode: str
    step_path: Path
    preview_path: Path
    summary_path: Path
    stl_path: Path | None
    name: str
    face_count: int
    edge_count: int
    solid_count: int
    bbox_min_mm: tuple[float, float, float]
    bbox_max_mm: tuple[float, float, float]
    spans_mm: tuple[float, float, float]
    major_axis: str
    volume_mm3: float | None
    surface_area_mm2: float | None


@dataclass(slots=True)
class RegionSelectionSummary:
    """Region selection summary for fixed and loaded end faces."""

    major_axis: str
    axis_index: int
    lower_threshold_mm: float
    upper_threshold_mm: float
    fixed_node_ids: list[int] = field(default_factory=list)
    load_node_ids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class MeshSummary:
    """Summary of the generated CalculiX-ready mesh."""

    inp_path: Path
    preview_path: Path
    summary_path: Path
    node_count: int
    element_count: int
    element_type_counts: dict[str, int]
    region_selection: RegionSelectionSummary
    geometry_step_path: Path
    mesh_size_mm: float


@dataclass(slots=True)
class SolverRunSummary:
    """Runtime details for a CalculiX subprocess call."""

    job_name: str
    run_dir: Path
    input_path: Path
    stdout_path: Path
    stderr_path: Path
    dat_path: Path
    frd_path: Path
    sta_path: Path
    cvg_path: Path | None
    return_code: int
    ccx_executable: str
    output_files: list[Path] = field(default_factory=list)


@dataclass(slots=True)
class ParsedResultSummary:
    """Parsed CalculiX output values."""

    job_name: str
    dat_path: Path
    summary_path: Path
    max_displacement_mm: float | None
    max_displacement_node: int | None
    max_von_mises_mpa: float | None
    max_von_mises_element: int | None
    estimated_safety_factor: float | None
    passes_displacement: bool | None
    passes_safety_factor: bool | None
    overall_pass: bool | None
    notes: list[str] = field(default_factory=list)
