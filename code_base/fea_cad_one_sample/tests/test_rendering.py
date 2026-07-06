"""Unit tests for STL rendering views."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.cad.execute_cadquery import execute_and_export_cadquery
from src.schemas.fea import SelectorHints
from src.visualization.compare_views import build_side_by_side_comparison, build_state_abc_grid
from src.visualization.render_views import render_support_load_annotation, render_views


def test_render_views_creates_standard_png_outputs(tmp_path: Path) -> None:
    """render_views creates front, side, top, iso, and grid PNG files."""

    geometry_dir = tmp_path / "geometry"
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=geometry_dir,
        basename="original",
    )

    views_dir = tmp_path / "views"
    result = render_views(geometry_dir / "original.stl", views_dir)

    assert (views_dir / "front.png").exists()
    assert (views_dir / "side.png").exists()
    assert (views_dir / "top.png").exists()
    assert (views_dir / "iso.png").exists()
    assert (views_dir / "grid.png").exists()
    assert result["front"] == str(views_dir / "front.png")
    assert result["iso"] == str(views_dir / "iso.png")
    assert result["grid"] == str(views_dir / "grid.png")


def test_render_views_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    """render_views preserves existing PNG outputs unless force=True."""

    geometry_dir = tmp_path / "geometry"
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=geometry_dir,
        basename="original",
    )

    views_dir = tmp_path / "views"
    views_dir.mkdir(parents=True)
    existing = views_dir / "front.png"
    existing.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="force=True"):
        render_views(geometry_dir / "original.stl", views_dir, force=False)

    assert existing.read_text(encoding="utf-8") == "keep"


def test_render_support_load_annotation_creates_annotated_png(tmp_path: Path) -> None:
    """render_support_load_annotation creates the State B annotation image."""

    geometry_dir = tmp_path / "geometry"
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=geometry_dir,
        basename="fea_revision",
    )

    output_path = tmp_path / "views" / "annotated_support_load.png"
    hints = SelectorHints(
        sample_id="sample-001",
        fixed_region_description="wall-facing mounting plate face",
        load_region_description="top face near free end",
        fixed_region_selector={"axis": "x", "side": "minimum"},
        load_region_selector={"axis": "x", "side": "maximum"},
    )
    result = render_support_load_annotation(geometry_dir / "fea_revision.stl", output_path, hints)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_build_side_by_side_comparison_creates_composite_image(tmp_path: Path) -> None:
    """build_side_by_side_comparison creates the comparison PNG."""

    original_geometry_dir = tmp_path / "original_geometry"
    fea_geometry_dir = tmp_path / "fea_geometry"
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=original_geometry_dir,
        basename="original",
    )
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(2, 2, 4)\n",
        output_dir=fea_geometry_dir,
        basename="fea_ready",
    )

    original_views_dir = tmp_path / "original_views"
    fea_views_dir = tmp_path / "fea_views"
    render_views(original_geometry_dir / "original.stl", original_views_dir)
    render_views(fea_geometry_dir / "fea_ready.stl", fea_views_dir)

    output_path = tmp_path / "comparison" / "side_by_side.png"
    result = build_side_by_side_comparison(original_views_dir, fea_views_dir, output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_build_state_abc_grid_creates_three_state_composite_image(tmp_path: Path) -> None:
    """build_state_abc_grid creates the three-state comparison PNG."""

    state_a_geometry_dir = tmp_path / "state_a_geometry"
    state_b_geometry_dir = tmp_path / "state_b_geometry"
    state_c_geometry_dir = tmp_path / "state_c_geometry"
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n",
        output_dir=state_a_geometry_dir,
        basename="state_a",
    )
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(2, 2, 4)\n",
        output_dir=state_b_geometry_dir,
        basename="state_b",
    )
    execute_and_export_cadquery(
        "import cadquery as cq\nresult = cq.Workplane().box(3, 2, 5)\n",
        output_dir=state_c_geometry_dir,
        basename="state_c",
    )

    state_a_views_dir = tmp_path / "state_a_views"
    state_b_views_dir = tmp_path / "state_b_views"
    state_c_views_dir = tmp_path / "state_c_views"
    render_views(state_a_geometry_dir / "state_a.stl", state_a_views_dir)
    render_views(state_b_geometry_dir / "state_b.stl", state_b_views_dir)
    render_views(state_c_geometry_dir / "state_c.stl", state_c_views_dir)

    output_path = tmp_path / "comparison" / "state_abc_grid.png"
    result = build_state_abc_grid(state_a_views_dir, state_b_views_dir, state_c_views_dir, output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
