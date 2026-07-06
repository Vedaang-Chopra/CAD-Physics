"""Unit tests for DB-original State A persistence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.cad.generate_original import generate_original_code
from src.schemas.config import PipelineConfig
from src.schemas.sample import CADSample


def test_generate_original_code_persists_database_original_artifacts(
    tmp_path: Path,
) -> None:
    """generate_original_code writes the canonical State A artifacts."""

    code = "import cadquery as cq\nresult = cq.Workplane().box(2, 3, 4)"
    sample = CADSample(
        sample_id="sample-001",
        prompt="Design a simple bracket.",
        prompt_variant="expert",
        source="cadcodeverify-db",
        metadata={"selection_mode": "sample_id"},
        ground_truth_code=code,
    )
    pipeline_config = PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=tmp_path / "config_gpt_5_4_mini.yaml",
        output_root=tmp_path / "outputs",
    )

    returned_code = generate_original_code(sample, pipeline_config)

    artifact_dir = pipeline_config.output_root / f"sample_{sample.sample_id}" / "01_dataset_original"
    code_path = artifact_dir / "database_original_code.py"
    prompt_path = artifact_dir / "original_prompt.txt"
    metadata_path = artifact_dir / "metadata.json"
    provenance_path = artifact_dir / "provenance.json"
    expected_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()

    assert returned_code == code
    assert prompt_path.read_text(encoding="utf-8") == sample.prompt
    assert code_path.read_text(encoding="utf-8") == code
    assert "original_raw_response.txt" not in {path.name for path in artifact_dir.iterdir()}

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

    assert metadata["sample_id"] == sample.sample_id
    assert metadata["database_original_code_path"] == str(code_path)
    assert metadata["code_hash_sha256"] == expected_hash
    assert provenance["code_hash_sha256"] == expected_hash
    assert provenance["code_path"] == str(code_path)
    assert provenance["prompt_path"] == str(prompt_path)


def test_generate_original_code_refuses_to_overwrite_existing_artifacts(
    tmp_path: Path,
) -> None:
    """generate_original_code preserves existing State A artifacts unless forced."""

    code = "import cadquery as cq\nresult = cq.Workplane().box(2, 3, 4)"
    sample = CADSample(
        sample_id="sample-001",
        prompt="Design a simple bracket.",
        prompt_variant="expert",
        source="cadcodeverify-db",
        metadata={"selection_mode": "sample_id"},
        ground_truth_code=code,
    )
    pipeline_config = PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=tmp_path / "config_gpt_5_4_mini.yaml",
        output_root=tmp_path / "outputs",
    )

    artifact_dir = pipeline_config.output_root / f"sample_{sample.sample_id}" / "01_dataset_original"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "database_original_code.py").write_text("keep", encoding="utf-8")
    (artifact_dir / "original_prompt.txt").write_text("keep", encoding="utf-8")
    (artifact_dir / "metadata.json").write_text("keep", encoding="utf-8")
    (artifact_dir / "provenance.json").write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="force=True"):
        generate_original_code(sample, pipeline_config)

    assert (artifact_dir / "database_original_code.py").read_text(encoding="utf-8") == "keep"
    assert (artifact_dir / "original_prompt.txt").read_text(encoding="utf-8") == "keep"
    assert (artifact_dir / "metadata.json").read_text(encoding="utf-8") == "keep"
    assert (artifact_dir / "provenance.json").read_text(encoding="utf-8") == "keep"


def test_generate_original_code_rejects_missing_ground_truth_code(tmp_path: Path) -> None:
    """generate_original_code raises when the DB original code is missing."""

    sample = CADSample(
        sample_id="sample-002",
        prompt="Design a simple bracket.",
        prompt_variant="expert",
        source="cadcodeverify-db",
        metadata={"selection_mode": "sample_id"},
        ground_truth_code=None,
    )
    pipeline_config = PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=tmp_path / "config_gpt_5_4_mini.yaml",
        output_root=tmp_path / "outputs",
    )

    with pytest.raises(LookupError, match="does not contain original CAD code"):
        generate_original_code(sample, pipeline_config)
