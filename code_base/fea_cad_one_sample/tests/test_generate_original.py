"""Unit tests for baseline CadQuery generation."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

from src.schemas.config import PipelineConfig
from src.schemas.sample import CADSample

generate_original_module = import_module("src.cad.generate_original")
validate_module = import_module("src.cad.validate_cad_script")

generate_original_code = generate_original_module.generate_original_code
extract_and_validate_cadquery_code = validate_module.extract_and_validate_cadquery_code
validate_cadquery_code = validate_module.validate_cadquery_code


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


def test_validate_cadquery_code_normalizes_and_accepts_cadquery() -> None:
    """validate_cadquery_code normalizes valid CadQuery source."""

    code = validate_cadquery_code(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n"
    )

    assert code.endswith("\n")
    assert "result = cq.Workplane()" in code


def test_extract_and_validate_cadquery_code_handles_json_payload() -> None:
    """extract_and_validate_cadquery_code extracts code from a JSON payload."""

    code = extract_and_validate_cadquery_code(
        '{"code_lines": ["import cadquery as cq", "result = cq.Workplane().box(1, 2, 3)"]}'
    )

    assert "box(1, 2, 3)" in code
    assert code.endswith("\n")


def test_generate_original_code_saves_artifacts_and_returns_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """generate_original_code writes artifacts and returns runnable code."""

    sample = CADSample(
        sample_id="sample-001",
        prompt="Design a simple bracket.",
        prompt_variant="expert",
        source="cadcodeverify-db",
        metadata={},
    )
    pipeline_config = PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=tmp_path / "config_gpt_5_4_mini.yaml",
        output_root=tmp_path / "outputs",
    )
    pipeline_config.config_path.write_text("model: {}\n", encoding="utf-8")

    raw_response = '{"code_lines": ["import cadquery as cq", "result = cq.Workplane().box(2, 3, 4)"]}'
    fake_connector = _FakeConnector(raw_response)

    monkeypatch.setattr("src.cad.generate_original.load_config", lambda **kwargs: {"model": {"id": "gpt-5.4-mini"}, "generation": {"expert_instruction": "Use CadQuery."}})
    monkeypatch.setattr("src.cad.generate_original.build_llm_connector", lambda model_config: fake_connector)
    monkeypatch.setattr("src.cad.generate_original.Generator", _FakeGenerator)

    code = generate_original_code(sample, pipeline_config)

    artifact_dir = pipeline_config.output_root / f"sample_{sample.sample_id}" / "01_original"
    assert "result = cq.Workplane().box(2, 3, 4)" in code
    assert (artifact_dir / "original_code.py").read_text(encoding="utf-8") == code
    assert (artifact_dir / "original_raw_response.txt").read_text(encoding="utf-8") == raw_response
    assert (artifact_dir / "metadata.json").exists()
    assert fake_connector.requests[0]["prompt"] == sample.prompt


def test_generate_original_code_refuses_to_overwrite_existing_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """generate_original_code preserves existing artifacts unless force=True."""

    sample = CADSample(
        sample_id="sample-001",
        prompt="Design a simple bracket.",
        prompt_variant="expert",
        source="cadcodeverify-db",
        metadata={},
    )
    pipeline_config = PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=tmp_path / "config_gpt_5_4_mini.yaml",
        output_root=tmp_path / "outputs",
    )
    pipeline_config.config_path.write_text("model: {}\n", encoding="utf-8")

    artifact_dir = pipeline_config.output_root / f"sample_{sample.sample_id}" / "01_original"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "original_code.py").write_text("keep", encoding="utf-8")
    (artifact_dir / "original_raw_response.txt").write_text("keep", encoding="utf-8")
    (artifact_dir / "metadata.json").write_text("keep", encoding="utf-8")

    monkeypatch.setattr("src.cad.generate_original.load_config", lambda **kwargs: {"model": {"id": "gpt-5.4-mini"}, "generation": {"expert_instruction": "Use CadQuery."}})
    monkeypatch.setattr("src.cad.generate_original.build_llm_connector", lambda model_config: pytest.fail("connector should not be built"))
    monkeypatch.setattr("src.cad.generate_original.Generator", _FakeGenerator)

    with pytest.raises(FileExistsError, match="force=True"):
        generate_original_code(sample, pipeline_config)

    assert (artifact_dir / "original_code.py").read_text(encoding="utf-8") == "keep"
    assert (artifact_dir / "original_raw_response.txt").read_text(encoding="utf-8") == "keep"
    assert (artifact_dir / "metadata.json").read_text(encoding="utf-8") == "keep"
