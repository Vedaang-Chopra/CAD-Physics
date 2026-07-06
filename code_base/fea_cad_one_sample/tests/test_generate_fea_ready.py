"""Unit tests for State B FEA revision generation."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

from src.schemas.config import PipelineConfig
from src.schemas.fea import LoadCase, SelectorHints

module = import_module("src.cad.generate_fea_ready")
revise_code_for_fea = module.revise_code_for_fea
execute_and_export_fea_revision_cadquery = module.execute_and_export_fea_revision_cadquery


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
    """Build a representative State B load case."""

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


def _sample_selector_hints() -> SelectorHints:
    """Build representative selector hints for State B."""

    return SelectorHints(
        sample_id="sample-001",
        fixed_region_description="wall-facing mounting plate face",
        load_region_description="top face near free end",
        fixed_region_selector={"axis": "x", "side": "minimum"},
        load_region_selector={"axis": "x", "side": "maximum"},
        notes=["Confirm support face.", "Confirm load face."],
    )


def test_revise_code_for_fea_writes_artifacts_and_returns_result(
    monkeypatch: pytest.MonkeyPatch,
    pipeline_config: PipelineConfig,
) -> None:
    """revise_code_for_fea writes State B artifacts and returns their paths."""

    load_case = _sample_load_case()
    selector_hints = _sample_selector_hints()
    raw_response = json.dumps(
        {
            "code_lines": [
                "import cadquery as cq",
                "result = cq.Workplane().box(3, 4, 5)",
            ],
            "change_log": {
                "sample_id": "sample-001",
                "source_state": "State A",
                "target_state": "State B",
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

    monkeypatch.setattr(
        "src.cad.generate_fea_ready.load_config",
        lambda **kwargs: {"model": {"id": "gpt-5.4-mini"}, "generation": {"expert_instruction": "Use CadQuery."}},
    )
    monkeypatch.setattr("src.cad.generate_fea_ready.build_llm_connector", lambda model_config: fake_connector)
    monkeypatch.setattr("src.cad.generate_fea_ready.Generator", _FakeGenerator)

    result = revise_code_for_fea(
        original_prompt="Design a simple bracket with a clear support face.",
        original_code="import cadquery as cq\nresult = cq.Workplane().box(20, 10, 5)",
        load_case=load_case,
        selector_hints=selector_hints,
        config=pipeline_config,
    )

    artifact_dir = pipeline_config.output_root / "sample_sample-001" / "02_fea_constrained_revision"
    assert result.sample_id == "sample-001"
    assert result.code_path == artifact_dir / "fea_revision_code.py"
    assert result.code_hash_sha256
    assert (artifact_dir / "fea_revision_prompt.txt").exists()
    assert (artifact_dir / "load_case.json").exists()
    assert (artifact_dir / "selector_hints.json").exists()
    assert (artifact_dir / "fea_revision_code.py").exists()
    assert (artifact_dir / "fea_revision_change_log.json").exists()
    assert (artifact_dir / "provenance.json").exists()
    assert result.view_paths["annotated_support_load"] == artifact_dir / "views" / "annotated_support_load.png"
    assert "result = cq.Workplane().box(3, 4, 5)" in result.code_path.read_text(encoding="utf-8")
    change_log = json.loads((artifact_dir / "fea_revision_change_log.json").read_text(encoding="utf-8"))
    assert change_log["sample_id"] == "sample-001"
    assert change_log["changed_features"][0]["feature"] == "rib"


def test_revise_code_for_fea_rejects_empty_original_prompt(
    monkeypatch: pytest.MonkeyPatch,
    pipeline_config: PipelineConfig,
) -> None:
    """revise_code_for_fea raises ValueError when the original prompt is empty."""

    monkeypatch.setattr(
        "src.cad.generate_fea_ready.load_config",
        lambda **kwargs: {"model": {"id": "gpt-5.4-mini"}, "generation": {"expert_instruction": "Use CadQuery."}},
    )

    with pytest.raises(ValueError, match="original_prompt"):
        revise_code_for_fea(
            original_prompt="",
            original_code="import cadquery as cq\nresult = cq.Workplane().box(20, 10, 5)",
            load_case=_sample_load_case(),
            selector_hints=_sample_selector_hints(),
            config=pipeline_config,
        )


def test_execute_and_export_fea_revision_cadquery_uses_fea_revision_basename(tmp_path: Path) -> None:
    """execute_and_export_fea_revision_cadquery writes the State B export filenames."""

    output_dir = tmp_path / "fea_revision"
    result = execute_and_export_fea_revision_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=output_dir,
    )

    assert (output_dir / "fea_revision.step").exists()
    assert (output_dir / "fea_revision.stl").exists()
    assert (output_dir / "execution_log.txt").exists()
    assert result["step_path"] == str(output_dir / "fea_revision.step")
    assert result["stl_path"] == str(output_dir / "fea_revision.stl")
