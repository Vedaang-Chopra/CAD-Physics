from pathlib import Path

import importlib

import src.interfaces as api

notebook_data = importlib.import_module("src.notebook_data")


def test_load_sample_from_dataset_reads_local_artifacts() -> None:
    module_root = Path(__file__).resolve().parents[1]
    dataset_dir = module_root / "outputs" / "sample_00689964" / "01_dataset_original"
    sample = api.load_sample_from_dataset(dataset_dir)

    assert sample.sample_id == "00689964"
    assert isinstance(sample.prompt, str) and sample.prompt.strip()
    assert isinstance(sample.ground_truth_code, str) and sample.ground_truth_code.strip()
    assert sample.metadata["load_source"] == "dataset"
    assert sample.metadata["database_original_code_path"].endswith("database_original_code.py")


def test_load_selected_sample_uses_db_loader(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_load_sample(connection_string: str, sample_id: str):
        calls["connection_string"] = connection_string
        calls["sample_id"] = sample_id
        return object()

    monkeypatch.setattr(notebook_data, "load_sample", fake_load_sample)
    result = api.load_selected_sample(
        module_root=Path(__file__).resolve().parents[1],
        sample_id="00689964",
        selection_source="db",
        connection_string="postgresql://example/db",
    )

    assert calls == {"connection_string": "postgresql://example/db", "sample_id": "00689964"}
    assert result is not None
