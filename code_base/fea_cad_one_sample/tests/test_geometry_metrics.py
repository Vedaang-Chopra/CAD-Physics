"""Unit tests for deterministic geometry metrics."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.cad.execute_cadquery import execute_and_export_cadquery
from src import interfaces


def test_compute_geometry_metrics_writes_metrics_and_pairwise_deltas(tmp_path: Path) -> None:
    """compute_geometry_metrics writes per-state metrics and deltas."""

    state_a_dir = tmp_path / "state_a"
    state_b_dir = tmp_path / "state_b"
    state_c_dir = tmp_path / "state_c"
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=state_a_dir,
        basename="state_a",
    )
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(2, 2, 4)\n",
        output_dir=state_b_dir,
        basename="state_b",
    )
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(3, 2, 5)\n",
        output_dir=state_c_dir,
        basename="state_c",
    )

    output_path = tmp_path / "03_comparison" / "geometry_metrics.json"
    payload = interfaces.compute_geometry_metrics(
        {
            "state_a": state_a_dir / "state_a.stl",
            "state_b": state_b_dir / "state_b.stl",
            "state_c": state_c_dir / "state_c.stl",
        },
        output_path,
    )

    loaded = interfaces.load_geometry_metrics(output_path)
    assert output_path.exists()
    assert loaded == payload
    assert payload["state_order"] == ["state_a", "state_b", "state_c"]
    assert payload["states"]["state_a"]["bounding_box_extents_mm"] == [1.0, 2.0, 3.0]
    assert payload["states"]["state_b"]["volume_mm3"] == pytest.approx(16.0)
    assert payload["states"]["state_c"]["surface_area_mm2"] == pytest.approx(62.0)
    assert payload["states"]["state_a"]["connected_component_count"] >= 1
    assert payload["states"]["state_a"]["is_watertight"] is True
    assert payload["pairwise_deltas"]["state_b_minus_state_a"]["volume_mm3"] == pytest.approx(10.0)
    assert payload["pairwise_deltas"]["state_c_minus_state_b"]["volume_mm3"] == pytest.approx(14.0)
    assert payload["pairwise_deltas"]["state_c_minus_state_a"]["bounding_box_extents_mm"] == [2.0, 0.0, 2.0]


def test_compute_geometry_metrics_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    """compute_geometry_metrics preserves existing JSON unless force=True."""

    output_path = tmp_path / "03_comparison" / "geometry_metrics.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("keep-me", encoding="utf-8")

    with pytest.raises(FileExistsError, match="force=True"):
        interfaces.compute_geometry_metrics({}, output_path, force=False)

    assert output_path.read_text(encoding="utf-8") == "keep-me"


def test_compute_geometry_metrics_rejects_missing_stl(tmp_path: Path) -> None:
    """compute_geometry_metrics raises FileNotFoundError for missing STL input."""

    output_path = tmp_path / "03_comparison" / "geometry_metrics.json"

    with pytest.raises(FileNotFoundError, match="STL file not found"):
        interfaces.compute_geometry_metrics({"state_a": tmp_path / "missing.stl"}, output_path, force=True)
