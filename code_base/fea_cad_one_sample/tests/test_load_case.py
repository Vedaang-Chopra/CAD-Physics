"""Unit tests for the FEA load-case writer."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from src.fea.write_load_case import MAX_VON_MISES_PA, write_load_case
from src.schemas.fea import LoadCase


def test_write_load_case_writes_expected_defaults(tmp_path: Path) -> None:
    """write_load_case writes the Aluminum 6061-T6 defaults to JSON."""

    output_path = tmp_path / "load_case.json"

    load_case = write_load_case("sample-001", output_path)

    expected = LoadCase(
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
                "description": "User-defined or model-inferred fixed support region",
                "selector": None,
            }
        ],
        loads=[
            {
                "id": "load_region",
                "type": "force",
                "magnitude_n": 200,
                "direction": [0, 0, -1],
                "description": "User-defined or model-inferred load application region",
                "selector": None,
            }
        ],
        requirements={
            "max_displacement_mm": 1.0,
            "required_safety_factor": 2.0,
            "max_von_mises_pa": 138_000_000,
        },
    )

    assert load_case == expected
    assert MAX_VON_MISES_PA == 138_000_000
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == asdict(expected)



def test_write_load_case_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    """write_load_case preserves existing JSON unless force=True."""

    output_path = tmp_path / "load_case.json"
    output_path.write_text("keep-me", encoding="utf-8")

    with pytest.raises(FileExistsError, match="force=True"):
        write_load_case("sample-001", output_path, force=False)

    assert output_path.read_text(encoding="utf-8") == "keep-me"
