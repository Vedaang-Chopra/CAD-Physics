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

    for name in required_names:
        assert hasattr(interfaces, name), name

    assert is_dataclass(interfaces.CADSample)
    assert is_dataclass(interfaces.PipelineConfig)
    assert is_dataclass(interfaces.LoadCase)
    assert is_dataclass(interfaces.ManualFEAReport)
    assert is_dataclass(interfaces.PipelineSummary)

    for name in required_names[5:]:
        assert callable(getattr(interfaces, name)), name
