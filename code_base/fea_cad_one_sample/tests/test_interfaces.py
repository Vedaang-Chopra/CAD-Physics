"""Unit tests for the public interface surface."""

from __future__ import annotations

from dataclasses import is_dataclass

from src import interfaces


def test_interfaces_reexport_core_public_names() -> None:
    """src.interfaces exposes the stable public types and functions."""

    required_names = [
        "CADSample",
        "PipelineConfig",
        "LoadCase",
        "SelectorHints",
        "RevisionChangeLog",
        "ManualFEAReport",
        "FEARevisionResult",
        "PostFEARevisionResult",
        "PipelineSummary",
        "inspect_schema",
        "load_sample",
        "generate_original_code",
        "execute_and_export_cadquery",
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
        "render_views",
        "render_support_load_annotation",
        "compute_geometry_metrics",
        "load_geometry_metrics",
        "build_side_by_side_comparison",
        "build_state_abc_grid",
        "build_comparison_artifacts",
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

    for name in required_names:
        assert hasattr(interfaces, name), name

    assert is_dataclass(interfaces.CADSample)
    assert is_dataclass(interfaces.PipelineConfig)
    assert is_dataclass(interfaces.LoadCase)
    assert is_dataclass(interfaces.SelectorHints)
    assert is_dataclass(interfaces.RevisionChangeLog)
    assert is_dataclass(interfaces.ManualFEAReport)
    assert is_dataclass(interfaces.FEARevisionResult)
    assert is_dataclass(interfaces.PostFEARevisionResult)
    assert is_dataclass(interfaces.PipelineSummary)

    for name in required_names[5:]:
        assert callable(getattr(interfaces, name)), name
