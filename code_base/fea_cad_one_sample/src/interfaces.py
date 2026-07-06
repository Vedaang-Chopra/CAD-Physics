"""Public interface surface for the one-sample FEA prototype."""

# pyright: reportMissingImports=false

from __future__ import annotations

from .cad.execute_cadquery import execute_and_export_cadquery
from .cad.generate_fea_ready import execute_and_export_fea_revision_cadquery, generate_fea_ready_code, revise_code_for_fea
from .cad.post_fea_revision import execute_and_export_post_fea_revision_cadquery, revise_code_after_fea
from .cad.generate_original import generate_original_code
from .db.load_sample import load_sample
from .notebook_data import load_sample_from_dataset, load_selected_sample
from .db.schema_inspection import inspect_schema
from .fea.freecad_manual_instructions import write_freecad_instructions
from .fea.manual_report import validate_manual_fea_completion, write_manual_fea_report_template
from .fea.post_fea_prompt import build_post_fea_prompt, validate_post_fea_inputs, write_post_fea_prompt
from .fea.write_load_case import write_load_case, write_selector_hints
from .fea_replication.geometry import prepare_geometry_artifacts
from .fea_replication.mesh import generate_calculix_mesh
from .fea_replication.pipeline import build_baseline_config, run_full_replication, run_parametric_load_study
from .fea_replication.results import parse_calculix_results
from .fea_replication.schemas import (
    BoundaryConditionSpec,
    FEAReplicationConfig,
    GeometrySpec,
    GeometrySummary,
    LoadSpec,
    MaterialSpec,
    MeshSummary,
    ParsedResultSummary,
    RegionSelectionSummary,
    SolverRunSummary,
    VerificationCriteria,
)
from .fea_replication.solver import run_calculix_solver
from .orchestration.pipeline import run_full_pipeline
from .prompts.build_fea_prompt import build_fea_prompt
from .reports.build_comparison_report import (
    build_change_log_summary,
    build_comparison_artifacts,
    build_final_experiment_report,
    build_geometry_metrics_markdown,
    build_post_fea_comparison_report,
    build_prompt_and_code_diffs_report,
)
from .schemas.config import PipelineConfig
from .schemas.fea import LoadCase, ManualFEAReport, RevisionChangeLog, SelectorHints
from .schemas.pipeline import FEARevisionResult, PipelineSummary, PostFEARevisionResult
from .schemas.sample import CADSample
from .visualization.compare_views import build_side_by_side_comparison, build_state_abc_grid
from .visualization.geometry_metrics import compute_geometry_metrics, load_geometry_metrics
from .visualization.render_views import render_views, render_support_load_annotation

__all__ = [
    "CADSample",
    "PipelineConfig",
    "GeometrySpec",
    "MaterialSpec",
    "LoadSpec",
    "BoundaryConditionSpec",
    "VerificationCriteria",
    "FEAReplicationConfig",
    "GeometrySummary",
    "RegionSelectionSummary",
    "MeshSummary",
    "SolverRunSummary",
    "ParsedResultSummary",
    "LoadCase",
    "SelectorHints",
    "RevisionChangeLog",
    "ManualFEAReport",
    "FEARevisionResult",
    "PostFEARevisionResult",
    "PipelineSummary",
    "inspect_schema",
    "load_sample",
    "load_sample_from_dataset",
    "load_selected_sample",
    "generate_original_code",
    "execute_and_export_cadquery",
    "build_baseline_config",
    "prepare_geometry_artifacts",
    "generate_calculix_mesh",
    "run_calculix_solver",
    "parse_calculix_results",
    "run_full_replication",
    "run_parametric_load_study",
    "build_fea_prompt",
    "write_load_case",
    "write_selector_hints",
    "generate_fea_ready_code",
    "revise_code_for_fea",
    "execute_and_export_fea_revision_cadquery",
    "revise_code_after_fea",
    "execute_and_export_post_fea_revision_cadquery",
    "build_post_fea_prompt",
    "validate_post_fea_inputs",
    "validate_manual_fea_completion",
    "compute_geometry_metrics",
    "load_geometry_metrics",
    "render_views",
    "render_support_load_annotation",
    "build_comparison_artifacts",
    "build_side_by_side_comparison",
    "build_state_abc_grid",
    "build_geometry_metrics_markdown",
    "build_prompt_and_code_diffs_report",
    "build_change_log_summary",
    "build_post_fea_comparison_report",
    "build_final_experiment_report",
    "write_freecad_instructions",
    "write_manual_fea_report_template",
    "write_post_fea_prompt",
    "run_full_pipeline",
]
