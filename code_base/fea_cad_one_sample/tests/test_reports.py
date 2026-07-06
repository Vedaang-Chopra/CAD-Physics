"""Unit tests for comparison markdown reports."""

from __future__ import annotations

from pathlib import Path

import pytest

from src import interfaces
from src.reports.build_comparison_report import (
    build_change_log_summary,
    build_comparison_artifacts,
    build_final_experiment_report,
    build_geometry_metrics_markdown,
    build_post_fea_comparison_report,
    build_prompt_and_code_diffs_report,
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


def test_build_phase4_comparison_reports_write_expected_artifacts(tmp_path: Path) -> None:
    """Phase 4 report builders write geometry metrics, diffs, and the final report."""

    state_a_geometry_dir = tmp_path / "state_a_geometry"
    state_b_geometry_dir = tmp_path / "state_b_geometry"
    state_c_geometry_dir = tmp_path / "state_c_geometry"
    interfaces.execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=state_a_geometry_dir,
        basename="state_a",
    )
    interfaces.execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(2, 2, 4)\n",
        output_dir=state_b_geometry_dir,
        basename="state_b",
    )
    interfaces.execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(3, 2, 5)\n",
        output_dir=state_c_geometry_dir,
        basename="state_c",
    )

    output_dir = tmp_path / "comparison"
    geometry_metrics_path = output_dir / "geometry_metrics.json"
    geometry_metrics = interfaces.compute_geometry_metrics(
        {
            "state_a": state_a_geometry_dir / "state_a.stl",
            "state_b": state_b_geometry_dir / "state_b.stl",
            "state_c": state_c_geometry_dir / "state_c.stl",
        },
        geometry_metrics_path,
    )
    geometry_md_path = build_geometry_metrics_markdown(geometry_metrics, output_dir / "geometry_metrics.md")
    diff_path = build_prompt_and_code_diffs_report(
        original_prompt="Design a simple bracket.",
        revision_prompt="Design a thicker bracket with a fixed support face.",
        original_code="import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        revision_code="import cadquery as cq\nresult = cq.Workplane().box(2, 2, 4)\n",
        post_revision_prompt="Design a post-FEA bracket with a thicker plate and clear support path.",
        post_revision_code="import cadquery as cq\nresult = cq.Workplane().box(3, 2, 5)\n",
        output_path=output_dir / "prompt_and_code_diffs.md",
    )
    change_log_path = build_change_log_summary(
        {
            "sample_id": "sample-001",
            "source_state": "State A",
            "target_state": "State B",
            "preserve_identity": True,
            "changed_features": [
                {
                    "feature": "plate thickness",
                    "change_type": "increased",
                    "reason": "Improve stiffness under the same load.",
                    "expected_effect": "Lower displacement and stress.",
                }
            ],
            "notes": ["Preserved the original hole pattern."],
        },
        output_dir / "change_log_summary.md",
    )
    final_report_path = build_final_experiment_report(
        sample_id="sample-001",
        output_dir=output_dir,
        geometry_metrics=geometry_metrics,
        prompt_and_code_diffs_path=diff_path,
        change_log_summary_path=change_log_path,
        state_abc_grid_path=output_dir / "state_abc_grid.png",
        report_summary=_completed_report(),
    )

    geometry_md = geometry_md_path.read_text(encoding="utf-8")
    diff_md = diff_path.read_text(encoding="utf-8")
    change_log_md = change_log_path.read_text(encoding="utf-8")
    final_report_md = final_report_path.read_text(encoding="utf-8")

    assert geometry_md_path.exists()
    assert diff_path.exists()
    assert change_log_path.exists()
    assert final_report_path.exists()
    assert "Geometry Metrics" in geometry_md
    assert "state_a" in geometry_md
    assert "state_b_minus_state_a" in geometry_md
    assert "A -> B" in diff_md
    assert "B -> C" in diff_md
    assert "Change Log Summary" in change_log_md
    assert "plate thickness" in change_log_md
    assert "Final Experiment Report" in final_report_md
    assert "What Changed Because Physical Constraints Were Introduced" in final_report_md
    assert "What Changed Because Actual FEA Feedback Was Introduced" in final_report_md
