"""Public interface surface for the one-sample FEA prototype."""

# pyright: reportMissingImports=false

from __future__ import annotations

from .cad.execute_cadquery import execute_and_export_cadquery
from .cad.generate_fea_ready import generate_fea_ready_code
from .cad.generate_original import generate_original_code
from .db.load_sample import load_sample
from .db.schema_inspection import inspect_schema
from .fea.freecad_manual_instructions import write_freecad_instructions
from .fea.manual_report import write_manual_fea_report_template
from .fea.post_fea_prompt import write_post_fea_prompt
from .fea.write_load_case import write_load_case
from .orchestration.pipeline import run_full_pipeline
from .prompts.build_fea_prompt import build_fea_prompt
from .reports.build_comparison_report import build_comparison_artifacts
from .schemas.config import PipelineConfig
from .schemas.fea import LoadCase, ManualFEAReport
from .schemas.pipeline import PipelineSummary
from .schemas.sample import CADSample
from .visualization.render_views import render_views

__all__ = [
    "CADSample",
    "PipelineConfig",
    "LoadCase",
    "ManualFEAReport",
    "PipelineSummary",
    "inspect_schema",
    "load_sample",
    "generate_original_code",
    "execute_and_export_cadquery",
    "build_fea_prompt",
    "write_load_case",
    "generate_fea_ready_code",
    "render_views",
    "build_comparison_artifacts",
    "write_freecad_instructions",
    "write_manual_fea_report_template",
    "write_post_fea_prompt",
    "run_full_pipeline",
]
