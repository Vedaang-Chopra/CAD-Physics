"""Unit tests for schema dataclasses in the one-sample FEA prototype."""

# pyright: reportMissingImports=false

from __future__ import annotations

from dataclasses import is_dataclass
from pathlib import Path

import pytest

from src.schemas.config import PipelineConfig
from src.schemas.fea import LoadCase, ManualFEAReport
from src.schemas.pipeline import PipelineSummary, RunManifestRecord
from src.schemas.sample import CADSample


def test_cad_sample_dataclass_happy_path() -> None:
    """CADSample exposes the expected fields and optional ground-truth code."""

    sample: CADSample = CADSample(
        sample_id="sample-001",
        prompt="Design a bracket.",
        prompt_variant="expert_prompt",
        source="cadcodeverify",
        metadata={"split": "train"},
    )

    assert is_dataclass(sample)
    assert sample.sample_id == "sample-001"
    assert sample.prompt_variant == "expert_prompt"
    assert sample.ground_truth_code is None
    assert sample.metadata == {"split": "train"}


def test_cad_sample_requires_required_fields() -> None:
    """CADSample raises TypeError when a required field is omitted."""

    sample_kwargs = {
        "sample_id": "sample-001",
        "prompt": "Design a bracket.",
        "prompt_variant": "expert_prompt",
        "source": "cadcodeverify",
    }

    with pytest.raises(TypeError):
        CADSample(**sample_kwargs)


def test_pipeline_config_defaults() -> None:
    """PipelineConfig keeps the configured paths and default runtime flags."""

    config: PipelineConfig = PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=Path("configs/config_gpt_5_4_mini.yaml"),
        output_root=Path("outputs"),
    )

    assert is_dataclass(config)
    assert config.force is False
    assert config.num_views == 4
    assert config.output_root == Path("outputs")


def test_load_case_dataclass_happy_path() -> None:
    """LoadCase stores the manual-FEA load definition fields."""

    load_case: LoadCase = LoadCase(
        sample_id="sample-001",
        units="SI",
        material={"name": "Aluminum 6061-T6"},
        boundary_conditions=[{"type": "fixed", "face": "base"}],
        loads=[{"type": "force", "value_n": 200}],
        requirements={"max_von_mises_pa": 138000000},
    )

    assert is_dataclass(load_case)
    assert load_case.material["name"] == "Aluminum 6061-T6"
    assert load_case.loads[0]["value_n"] == 200


def test_manual_fea_report_dataclass_happy_path() -> None:
    """ManualFEAReport stores manual solver results and notes."""

    report: ManualFEAReport = ManualFEAReport(
        sample_id="sample-001",
        solver="CalculiX",
        manual_run=True,
        max_von_mises_pa=1.2e8,
        max_displacement_mm=0.4,
        yield_strength_pa=2.76e8,
        required_safety_factor=2.0,
        computed_safety_factor=2.3,
        passes_stress=True,
        passes_displacement=True,
        overall_pass=True,
        stress_hotspot_description="Upper fillet near load face.",
        notes=["Manual run completed."],
    )

    assert is_dataclass(report)
    assert report.overall_pass is True
    assert report.notes == ["Manual run completed."]


def test_pipeline_summary_dataclass_happy_path() -> None:
    """PipelineSummary stores run-level status and artifact mappings."""

    summary: PipelineSummary = PipelineSummary(
        sample_id="sample-001",
        output_dir=Path("outputs/sample-001"),
        stage_statuses={"original": "passed"},
        artifact_paths={"original.step": "outputs/sample-001/01_original/original.step"},
        failures=[],
    )

    assert is_dataclass(summary)
    assert summary.stage_statuses["original"] == "passed"
    assert summary.output_dir == Path("outputs/sample-001")


def test_run_manifest_record_defaults() -> None:
    """RunManifestRecord accepts a valid stage status and optional notes."""

    record: RunManifestRecord = RunManifestRecord(
        stage_name="original_export",
        status="passed",
        artifact_paths={"original.step": "outputs/sample-001/01_original/original.step"},
    )

    assert is_dataclass(record)
    assert record.status == "passed"
    assert record.notes is None
