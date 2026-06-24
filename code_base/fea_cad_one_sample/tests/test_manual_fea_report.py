"""Unit tests for manual FEA report and post-FEA prompt artifacts."""

# pyright: reportMissingImports=false

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.fea.manual_report import write_manual_fea_report_template
from src.fea.post_fea_prompt import write_post_fea_prompt
from src.schemas.fea import LoadCase, ManualFEAReport


def _sample_load_case() -> LoadCase:
    """Build a representative load case for post-FEA prompt tests."""

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


def _completed_report_data() -> dict[str, object]:
    """Build a filled manual report for post-FEA prompt tests."""

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


def test_write_manual_fea_report_template_writes_expected_json(tmp_path: Path) -> None:
    """write_manual_fea_report_template writes the expected blank report template."""

    output_path = tmp_path / "fea_report.json"

    report = write_manual_fea_report_template("sample-001", output_path)

    expected = ManualFEAReport(
        sample_id="sample-001",
        solver="FreeCAD FEM + CalculiX",
        manual_run=True,
        max_von_mises_pa=None,
        max_displacement_mm=None,
        yield_strength_pa=276_000_000,
        required_safety_factor=2.0,
        computed_safety_factor=None,
        passes_stress=None,
        passes_displacement=None,
        overall_pass=None,
        stress_hotspot_description="",
        notes=[],
    )

    assert report == expected
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == {
        "sample_id": "sample-001",
        "solver": "FreeCAD FEM + CalculiX",
        "manual_run": True,
        "max_von_mises_pa": None,
        "max_displacement_mm": None,
        "yield_strength_pa": 276_000_000,
        "required_safety_factor": 2.0,
        "computed_safety_factor": None,
        "passes_stress": None,
        "passes_displacement": None,
        "overall_pass": None,
        "stress_hotspot_description": "",
        "notes": [],
    }


def test_write_manual_fea_report_template_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    """write_manual_fea_report_template preserves existing files unless force=True."""

    output_path = tmp_path / "fea_report.json"
    output_path.write_text("keep-me", encoding="utf-8")

    with pytest.raises(FileExistsError, match="force=True"):
        write_manual_fea_report_template("sample-001", output_path, force=False)

    assert output_path.read_text(encoding="utf-8") == "keep-me"


def test_write_post_fea_prompt_writes_feedback_prompt_and_comparison(tmp_path: Path) -> None:
    """write_post_fea_prompt writes both post-FEA markdown artifacts."""

    output_dir = tmp_path / "05_post_fea_refinement"
    report_path = tmp_path / "fea_report.json"
    report_path.write_text(json.dumps(_completed_report_data(), indent=2, sort_keys=True), encoding="utf-8")

    result = write_post_fea_prompt(
        sample_id="sample-001",
        load_case=_sample_load_case(),
        report_path=report_path,
        output_dir=output_dir,
    )

    feedback_prompt_path = output_dir / "fea_feedback_prompt.txt"
    comparison_path = output_dir / "comparison_after_fea.md"
    feedback_text = feedback_prompt_path.read_text(encoding="utf-8")
    comparison_text = comparison_path.read_text(encoding="utf-8")

    assert result["fea_feedback_prompt_path"] == str(feedback_prompt_path)
    assert result["comparison_after_fea_path"] == str(comparison_path)
    assert "The CAD design was tested using FreeCAD FEM + CalculiX." in feedback_text
    assert "Keep the original design intent." in feedback_text
    assert "Max von Mises stress: 120000000" in feedback_text
    assert "Use one connected solid." in feedback_text
    assert "Post-FEA Comparison Template" in comparison_text
    assert "FEA Result Summary" in comparison_text
    assert "Original CAD" in comparison_text
    assert "Post-FEA refined CAD" in comparison_text
    assert "What Changed Because of Physics Feedback" in comparison_text


def test_write_post_fea_prompt_handles_pending_values(tmp_path: Path) -> None:
    """write_post_fea_prompt can produce placeholder text when the manual report is blank."""

    output_dir = tmp_path / "05_post_fea_refinement"
    report_path = tmp_path / "fea_report.json"
    write_manual_fea_report_template("sample-001", report_path)

    result = write_post_fea_prompt(
        sample_id="sample-001",
        load_case=_sample_load_case(),
        report_path=report_path,
        output_dir=output_dir,
    )

    feedback_text = (output_dir / "fea_feedback_prompt.txt").read_text(encoding="utf-8")
    comparison_text = (output_dir / "comparison_after_fea.md").read_text(encoding="utf-8")

    assert result["fea_feedback_prompt_path"].endswith("fea_feedback_prompt.txt")
    assert "<pending>" in feedback_text
    assert "<pending>" in comparison_text


def test_write_post_fea_prompt_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    """write_post_fea_prompt preserves existing outputs unless force=True."""

    output_dir = tmp_path / "05_post_fea_refinement"
    output_dir.mkdir(parents=True)
    (output_dir / "fea_feedback_prompt.txt").write_text("keep-prompt", encoding="utf-8")

    report_path = tmp_path / "fea_report.json"
    report_path.write_text(json.dumps(_completed_report_data(), indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(FileExistsError, match="force=True"):
        write_post_fea_prompt(
            sample_id="sample-001",
            load_case=_sample_load_case(),
            report_path=report_path,
            output_dir=output_dir,
            force=False,
        )

    assert (output_dir / "fea_feedback_prompt.txt").read_text(encoding="utf-8") == "keep-prompt"
