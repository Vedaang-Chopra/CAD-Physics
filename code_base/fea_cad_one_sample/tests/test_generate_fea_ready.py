"""Unit tests for FEA-ready CadQuery generation."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

from src.schemas.config import PipelineConfig

module = import_module("src.cad.generate_fea_ready")
generate_fea_ready_code = module.generate_fea_ready_code
execute_and_export_fea_ready_cadquery = module.execute_and_export_fea_ready_cadquery


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
        output_root=tmp_path / "outputs" / "sample_sample-001",
    )


def test_generate_fea_ready_code_writes_artifact_and_returns_code(
    monkeypatch: pytest.MonkeyPatch,
    pipeline_config: PipelineConfig,
) -> None:
    """generate_fea_ready_code writes the FEA-ready code artifact."""

    raw_response = '{"code_lines": ["import cadquery as cq", "result = cq.Workplane().box(3, 4, 5)"]}'
    fake_connector = _FakeConnector(raw_response)

    monkeypatch.setattr(
        "src.cad.generate_fea_ready.load_config",
        lambda **kwargs: {"model": {"id": "gpt-5.4-mini"}, "generation": {"expert_instruction": "Use CadQuery."}},
    )
    monkeypatch.setattr("src.cad.generate_fea_ready.build_llm_connector", lambda model_config: fake_connector)
    monkeypatch.setattr("src.cad.generate_fea_ready.Generator", _FakeGenerator)

    code = generate_fea_ready_code("Generate an FEA-ready bracket.", pipeline_config)

    artifact_dir = pipeline_config.output_root / "02_fea_ready"
    assert "result = cq.Workplane().box(3, 4, 5)" in code
    assert (artifact_dir / "fea_ready_code.py").read_text(encoding="utf-8") == code
    assert fake_connector.requests[0]["prompt"] == "Generate an FEA-ready bracket."


def test_generate_fea_ready_code_writes_failure_artifact(
    monkeypatch: pytest.MonkeyPatch,
    pipeline_config: PipelineConfig,
) -> None:
    """generate_fea_ready_code writes a readable failure artifact and preserves prior outputs."""

    fake_connector = _FakeConnector("not python")
    pipeline_config.force = True

    artifact_dir = pipeline_config.output_root / "02_fea_ready"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    code_path = artifact_dir / "fea_ready_code.py"
    code_path.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(
        "src.cad.generate_fea_ready.load_config",
        lambda **kwargs: {"model": {"id": "gpt-5.4-mini"}, "generation": {"expert_instruction": "Use CadQuery."}},
    )
    monkeypatch.setattr("src.cad.generate_fea_ready.build_llm_connector", lambda model_config: fake_connector)
    monkeypatch.setattr("src.cad.generate_fea_ready.Generator", _FakeGenerator)

    with pytest.raises(Exception):
        generate_fea_ready_code("Generate an FEA-ready bracket.", pipeline_config)

    failure_path = artifact_dir / "fea_ready_failure.txt"
    assert failure_path.exists()
    assert code_path.read_text(encoding="utf-8") == "keep"
    failure_text = failure_path.read_text(encoding="utf-8")
    assert "FEA-ready generation failed." in failure_text
    assert "not python" in failure_text


def test_execute_and_export_fea_ready_cadquery_uses_fea_ready_basename(tmp_path: Path) -> None:
    """execute_and_export_fea_ready_cadquery writes the FEA-ready export filenames."""

    output_dir = tmp_path / "fea_ready"
    result = execute_and_export_fea_ready_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=output_dir,
    )

    assert (output_dir / "fea_ready.step").exists()
    assert (output_dir / "fea_ready.stl").exists()
    assert (output_dir / "execution_log.txt").exists()
    assert result["step_path"] == str(output_dir / "fea_ready.step")
    assert result["stl_path"] == str(output_dir / "fea_ready.stl")
