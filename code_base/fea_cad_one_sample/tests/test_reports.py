"""Unit tests for comparison markdown reports."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.reports.build_comparison_report import (
    build_comparison_artifacts,
    build_post_fea_comparison_report,
)
from src.schemas.fea import LoadCase


def _sample_load_case() -> LoadCase:
    """Build a representative load case for post-FEA comparison tests."""

    return LoadCase(
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
                "description": "fixed/support face",
                "selector": None,
            }
        ],
        loads=[
            {
                "id": "load_region",
                "type": "force",
                "magnitude_n": 200,
                "direction": [0, 0, -1],
                "description": "load face",
                "selector": None,
            }
        ],
        requirements={
            "max_displacement_mm": 1.0,
            "required_safety_factor": 2.0,
            "max_von_mises_pa": 138_000_000,
        },
    )


def _completed_report() -> dict[str, object]:
    """Build a filled manual report for post-FEA comparison tests."""

    return {
        "sample_id": "sample-001",
        "solver": "FreeCAD FEM + CalculiX",
        "manual_run": True,
        "max_von_mises_pa": 120_000_000,
        "max_displacement_mm": 0.4,
        "yield_strength_pa": 276_000_000,
        "required_safety_factor": 2.0,
        "computed_safety_factor": 2.3,
        "passes_stress": True,
        "passes_displacement": True,
        "overall_pass": True,
        "stress_hotspot_description": "Upper fillet near the load face.",
        "notes": ["Manual run completed."],
    }


def test_build_comparison_artifacts_writes_markdown_files(tmp_path: Path) -> None:
    """build_comparison_artifacts writes prompt and geometry markdown reports."""

    output_dir = tmp_path / "comparison"
    result = build_comparison_artifacts(
        original_prompt="Design a simple bracket.",
        fea_prompt="Design a thicker bracket with a fixed support face.",
        output_dir=output_dir,
        notes={
            "what changed visually?": "The FEA-ready part is thicker.",
            "why the change happened": "To improve meshability and strength.",
        },
    )

    prompt_diff_path = output_dir / "prompt_diff.md"
    geometry_notes_path = output_dir / "geometry_diff_notes.md"
    assert prompt_diff_path.exists()
    assert geometry_notes_path.exists()
    assert result["prompt_diff"] == str(prompt_diff_path)
    assert result["geometry_diff_notes"] == str(geometry_notes_path)
    assert "Unified Diff" in prompt_diff_path.read_text(encoding="utf-8")
    assert "FEA-ready part is thicker" in geometry_notes_path.read_text(encoding="utf-8")


def test_build_post_fea_comparison_report_writes_template(tmp_path: Path) -> None:
    """build_post_fea_comparison_report writes the post-FEA comparison template."""

    output_dir = tmp_path / "comparison_after_fea"
    output_path = build_post_fea_comparison_report(
        sample_id="sample-001",
        load_case=_sample_load_case(),
        report=_completed_report(),
        output_dir=output_dir,
    )

    text = output_path.read_text(encoding="utf-8")
    assert output_path.exists()
    assert "Post-FEA Comparison Template" in text
    assert "FEA Result Summary" in text
    assert "Max von Mises stress: 120000000 Pa" in text
    assert "Comparison Matrix" in text
    assert "Original CAD" in text
    assert "Post-FEA refined CAD" in text
    assert "What Changed Because of Physics Feedback" in text


def test_build_comparison_artifacts_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    """build_comparison_artifacts preserves existing outputs unless force=True."""

    output_dir = tmp_path / "comparison"
    output_dir.mkdir(parents=True)
    prompt_diff_path = output_dir / "prompt_diff.md"
    geometry_notes_path = output_dir / "geometry_diff_notes.md"
    prompt_diff_path.write_text("keep-prompt", encoding="utf-8")
    geometry_notes_path.write_text("keep-notes", encoding="utf-8")

    with pytest.raises(FileExistsError, match="force=True"):
        build_comparison_artifacts(
            original_prompt="Design a simple bracket.",
            fea_prompt="Design a thicker bracket with a fixed support face.",
            output_dir=output_dir,
            notes={"why the change happened": "To improve meshability and strength."},
            force=False,
        )

    assert prompt_diff_path.read_text(encoding="utf-8") == "keep-prompt"
    assert geometry_notes_path.read_text(encoding="utf-8") == "keep-notes"
