"""Unit tests for State C post-FEA revision generation."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

from src.fea.manual_report import required_manual_fea_evidence_paths
from src.schemas.config import PipelineConfig
from src.schemas.fea import LoadCase

module = import_module("src.cad.post_fea_revision")
revise_code_after_fea = module.revise_code_after_fea
execute_and_export_post_fea_revision_cadquery = module.execute_and_export_post_fea_revision_cadquery


class _FakeConnector:
    def __init__(self, raw_response: str) -> None:
        self.raw_response = raw_response
        self.requests: list[dict[str, object]] = []

    def generate(self, **kwargs: object) -> str:
        self.requests.append(dict(kwargs))
        return self.raw_response


class _FakeGenerator:
    def __init__(self, connector: Any, config: dict[str, object]) -> None:
        self.connector = connector
        self.config = config

    def generate_code_raw(self, prompt: str, system_instruction: str | None = None, preformatted: bool = False) -> str:
        return self.connector.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            preformatted=preformatted,
        )


@pytest.fixture()
def pipeline_config(tmp_path: Path) -> PipelineConfig:
    """Create a pipeline config with a per-sample output root."""

    config_path = tmp_path / "config_gpt_5_4_mini.yaml"
    config_path.write_text("model: {}\n", encoding="utf-8")
    return PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=config_path,
        output_root=tmp_path / "outputs",
    )


def _sample_load_case() -> LoadCase:
    """Build a representative State C load case."""

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
                "description": "Wall-facing mounting plate face",
                "selector": None,
            }
        ],
        loads=[
            {
                "id": "load_region",
                "type": "force",
                "magnitude_n": 200,
                "direction": [0, 0, -1],
                "description": "Top face near free end",
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
    """Build a complete manual FEA report for State C tests."""

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


def test_revise_code_after_fea_writes_artifacts_and_returns_result(
    monkeypatch: pytest.MonkeyPatch,
    pipeline_config: PipelineConfig,
    tmp_path: Path,
) -> None:
    """revise_code_after_fea writes State C prompt/code/change-log/provenance artifacts."""

    load_case = _sample_load_case()
    raw_response = json.dumps(
        {
            "code_lines": [
                "import cadquery as cq",
                "result = cq.Workplane().box(4, 5, 6)",
            ],
            "change_log": {
                "sample_id": "sample-001",
                "source_state": "State B",
                "target_state": "State C",
                "preserve_identity": True,
                "changed_features": [
                    {
                        "feature": "rib",
                        "change_type": "added",
                        "reason": "Improve stiffness near the load path.",
                        "expected_effect": "Reduce deflection.",
                    }
                ],
                "notes": ["Preserve silhouette."],
            },
        }
    )
    fake_connector = _FakeConnector(raw_response)

    screenshot_paths = required_manual_fea_evidence_paths(tmp_path / "04_manual_freecad_fea")
    for path in screenshot_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("image-bytes", encoding="utf-8")

    monkeypatch.setattr(
        "src.cad.post_fea_revision.load_config",
        lambda **kwargs: {"model": {"id": "gpt-5.4-mini"}, "generation": {"expert_instruction": "Use CadQuery."}},
    )
    monkeypatch.setattr("src.cad.post_fea_revision.build_llm_connector", lambda model_config: fake_connector)
    monkeypatch.setattr("src.cad.post_fea_revision.Generator", _FakeGenerator)

    result = revise_code_after_fea(
        fea_revision_code="import cadquery as cq\nresult = cq.Workplane().box(3, 4, 5)",
        load_case=load_case,
        fea_report=_completed_report(),
        screenshots=screenshot_paths,
        config=pipeline_config,
    )

    artifact_dir = pipeline_config.output_root / "sample_sample-001" / "05_post_fea_revision"
    assert result.sample_id == "sample-001"
    assert result.prompt_path == artifact_dir / "post_fea_prompt.txt"
    assert result.code_path == artifact_dir / "post_fea_code.py"
    assert result.manual_report_path == pipeline_config.output_root / "sample_sample-001" / "04_manual_freecad_fea" / "fea_report.json"
    assert result.screenshot_paths == screenshot_paths
    assert result.code_hash_sha256
    assert (artifact_dir / "post_fea_prompt.txt").exists()
    assert (artifact_dir / "post_fea_code.py").exists()
    assert (artifact_dir / "post_fea_change_log.json").exists()
    assert (artifact_dir / "provenance.json").exists()
    assert "result = cq.Workplane().box(4, 5, 6)" in result.code_path.read_text(encoding="utf-8")
    prompt_text = result.prompt_path.read_text(encoding="utf-8")
    assert "State B Code" in prompt_text
    assert "Manual FEA Results" in prompt_text
    assert "Upper fillet near the load face." in prompt_text
    change_log = json.loads((artifact_dir / "post_fea_change_log.json").read_text(encoding="utf-8"))
    assert change_log["sample_id"] == "sample-001"
    assert change_log["target_state"] == "State C"


def test_revise_code_after_fea_blocks_when_manual_evidence_missing(
    monkeypatch: pytest.MonkeyPatch,
    pipeline_config: PipelineConfig,
) -> None:
    """revise_code_after_fea refuses to call the model when manual evidence is incomplete."""

    fake_connector = _FakeConnector("should not be used")
    monkeypatch.setattr(
        "src.cad.post_fea_revision.load_config",
        lambda **kwargs: {"model": {"id": "gpt-5.4-mini"}, "generation": {"expert_instruction": "Use CadQuery."}},
    )
    monkeypatch.setattr("src.cad.post_fea_revision.build_llm_connector", lambda model_config: fake_connector)
    monkeypatch.setattr("src.cad.post_fea_revision.Generator", _FakeGenerator)

    with pytest.raises(ValueError, match="State C blocked"):
        revise_code_after_fea(
            fea_revision_code="import cadquery as cq\nresult = cq.Workplane().box(3, 4, 5)",
            load_case=_sample_load_case(),
            fea_report={"sample_id": "sample-001"},
            screenshots=[],
            config=pipeline_config,
        )

    assert fake_connector.requests == []


def test_execute_and_export_post_fea_revision_cadquery_uses_post_fea_basename(tmp_path: Path) -> None:
    """execute_and_export_post_fea_revision_cadquery writes the State C export filenames."""

    output_dir = tmp_path / "post_fea_revision"
    result = execute_and_export_post_fea_revision_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=output_dir,
    )

    assert (output_dir / "post_fea.step").exists()
    assert (output_dir / "post_fea.stl").exists()
    assert (output_dir / "execution_log.txt").exists()
    assert result["step_path"] == str(output_dir / "post_fea.step")
    assert result["stl_path"] == str(output_dir / "post_fea.stl")
