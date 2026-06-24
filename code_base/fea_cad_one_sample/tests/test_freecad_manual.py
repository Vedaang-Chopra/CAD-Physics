"""Unit tests for manual FreeCAD FEM instructions."""

# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from src.fea.freecad_manual_instructions import write_freecad_instructions
from src.schemas.fea import LoadCase


def _sample_load_case() -> LoadCase:
    """Build a representative load case for manual FreeCAD instructions tests."""

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


def test_write_freecad_instructions_writes_required_steps(tmp_path: Path) -> None:
    """write_freecad_instructions writes the required manual workflow text."""

    output_path = tmp_path / "freecad_instructions.md"
    step_path = tmp_path / "fea_ready.step"
    step_path.write_text("solid", encoding="utf-8")

    result_path = write_freecad_instructions(
        sample_id="sample-001",
        step_path=step_path,
        load_case=_sample_load_case(),
        output_path=output_path,
    )

    text = output_path.read_text(encoding="utf-8")
    assert result_path == output_path
    assert output_path.exists()
    assert "Open FreeCAD." in text
    assert f"Import {step_path.name}." in text
    assert "Switch to the FEM workbench." in text
    assert "Assign material: Aluminum 6061-T6." in text
    assert "Add a force constraint: 200 N downward" in text
    assert "Create the mesh using Gmsh or Netgen." in text
    assert "Run CalculiX manually." in text
    assert "mesh.png" in text
    assert "von_mises.png" in text
    assert "max displacement" in text


def test_write_freecad_instructions_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    """write_freecad_instructions preserves an existing file unless force=True."""

    output_path = tmp_path / "freecad_instructions.md"
    output_path.write_text("keep-me", encoding="utf-8")

    with pytest.raises(FileExistsError, match="force=True"):
        write_freecad_instructions(
            sample_id="sample-001",
            step_path=tmp_path / "fea_ready.step",
            load_case=_sample_load_case(),
            output_path=output_path,
            force=False,
        )

    assert output_path.read_text(encoding="utf-8") == "keep-me"
