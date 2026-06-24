"""Unit tests for CadQuery execution and export."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest

execute_cadquery_module = import_module("src.cad.execute_cadquery")
execute_and_export_cadquery = execute_cadquery_module.execute_and_export_cadquery


def test_execute_and_export_cadquery_exports_step_and_stl(tmp_path: Path) -> None:
    """A simple CadQuery box should export STEP and STL files."""

    output_dir = tmp_path / "original"
    result = execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=output_dir,
        basename="original",
    )

    step_path = output_dir / "original.step"
    stl_path = output_dir / "original.stl"
    log_path = output_dir / "execution_log.txt"

    assert result["success"] is True
    assert step_path.exists()
    assert stl_path.exists()
    assert log_path.exists()
    assert result["step_path"] == str(step_path)
    assert result["stl_path"] == str(stl_path)
    assert "status: success" in log_path.read_text(encoding="utf-8")


def test_execute_and_export_cadquery_refuses_overwrite_without_force(tmp_path: Path) -> None:
    """Existing outputs are preserved unless force=True."""

    output_dir = tmp_path / "original"
    output_dir.mkdir(parents=True)
    step_path = output_dir / "original.step"
    stl_path = output_dir / "original.stl"
    log_path = output_dir / "execution_log.txt"
    step_path.write_text("keep-step", encoding="utf-8")
    stl_path.write_text("keep-stl", encoding="utf-8")
    log_path.write_text("keep-log", encoding="utf-8")

    with pytest.raises(FileExistsError, match="force=True"):
        execute_and_export_cadquery(
            "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
            output_dir=output_dir,
            basename="original",
            force=False,
        )

    assert step_path.read_text(encoding="utf-8") == "keep-step"
    assert stl_path.read_text(encoding="utf-8") == "keep-stl"
    assert log_path.read_text(encoding="utf-8") == "keep-log"


def test_execute_and_export_cadquery_overwrites_when_forced(tmp_path: Path) -> None:
    """force=True replaces the existing baseline outputs."""

    output_dir = tmp_path / "original"
    output_dir.mkdir(parents=True)
    step_path = output_dir / "original.step"
    stl_path = output_dir / "original.stl"
    log_path = output_dir / "execution_log.txt"
    step_path.write_text("keep-step", encoding="utf-8")
    stl_path.write_text("keep-stl", encoding="utf-8")
    log_path.write_text("keep-log", encoding="utf-8")

    result = execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=output_dir,
        basename="original",
        force=True,
    )

    assert result["success"] is True
    assert step_path.exists()
    assert stl_path.exists()
    assert log_path.exists()
    assert step_path.read_bytes() != b"keep-step"
    assert stl_path.read_bytes() != b"keep-stl"
    assert "status: success" in log_path.read_text(encoding="utf-8")
