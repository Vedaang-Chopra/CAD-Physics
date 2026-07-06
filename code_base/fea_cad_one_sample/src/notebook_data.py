"""Notebook helpers for loading sample artifacts in a consistent way."""

from __future__ import annotations

import json
from pathlib import Path

from .db.load_sample import load_sample
from .schemas.sample import CADSample


def load_sample_from_dataset(dataset_original_dir: Path) -> CADSample:
    """Load a CADSample directly from stored dataset artifacts."""

    dataset_original_dir = Path(dataset_original_dir)
    metadata_path = dataset_original_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Dataset metadata not found: {metadata_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    prompt_path = Path(metadata.get("original_prompt_path") or (dataset_original_dir / "original_prompt.txt"))
    code_path = Path(metadata.get("database_original_code_path") or (dataset_original_dir / "database_original_code.py"))
    if not prompt_path.exists():
        raise FileNotFoundError(f"Dataset prompt not found: {prompt_path}")
    if not code_path.exists():
        raise FileNotFoundError(f"Dataset code not found: {code_path}")

    prompt = prompt_path.read_text(encoding="utf-8")
    code_text = code_path.read_text(encoding="utf-8")
    sample_id = str(metadata.get("sample_id") or dataset_original_dir.parent.name.removeprefix("sample_"))
    prompt_variant = str(metadata.get("prompt_variant") or "expert")
    source = str(metadata.get("source") or "local-dataset")

    metadata_payload = dict(metadata)
    metadata_payload.update(
        {
            "load_source": "dataset",
            "dataset_original_dir": str(dataset_original_dir),
            "original_prompt_path": str(prompt_path),
            "database_original_code_path": str(code_path),
            "selection_mode": metadata_payload.get("selection_mode", "dataset_path"),
        }
    )
    return CADSample(
        sample_id=sample_id,
        prompt=prompt,
        prompt_variant=prompt_variant,
        source=source,
        metadata=metadata_payload,
        ground_truth_code=code_text,
    )


def load_selected_sample(
    *,
    module_root: Path,
    sample_id: str,
    selection_source: str,
    connection_string: str | None = None,
) -> CADSample:
    """Load the notebook sample using the selected source mode."""

    normalized_source = selection_source.strip().lower()
    dataset_original_dir = Path(module_root) / "outputs" / f"sample_{sample_id}" / "01_dataset_original"
    if normalized_source == "dataset":
        return load_sample_from_dataset(dataset_original_dir)
    if normalized_source == "db":
        if not connection_string:
            raise ValueError("connection_string is required when selection_source='db'.")
        return load_sample(connection_string, sample_id=sample_id)
    raise ValueError(f"Unknown selection_source: {selection_source!r}")
