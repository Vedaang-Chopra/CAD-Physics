"""Geometry loading, fallback generation, and preview rendering."""

# pyright: reportMissingImports=false

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import cadquery as cq

from src.cad.export_geometry import export_step_and_stl

from .schemas import FEAReplicationConfig, GeometrySummary
from .utils import write_json

logger = logging.getLogger(__name__)


def prepare_geometry_artifacts(config: FEAReplicationConfig, *, force: bool = False) -> GeometrySummary:
    """Prepare the geometry STEP source, preview, and summary files."""

    logger.info(
        "prepare_geometry_artifacts | start | run_dir=%s | source_step_path=%s | force=%s",
        config.run_dir,
        config.geometry.source_step_path,
        force,
    )
    try:
        run_dir = Path(config.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        step_path = run_dir / f"{config.geometry.placeholder_name}.step"
        stl_path = run_dir / f"{config.geometry.placeholder_name}.stl"
        summary_path = run_dir / "geometry_summary.json"
        preview_path = run_dir / "geometry_preview.png"

        if config.geometry.source_step_path and Path(config.geometry.source_step_path).exists():
            summary = _copy_existing_step(
                source_step_path=Path(config.geometry.source_step_path),
                step_path=step_path,
                stl_path=stl_path,
                preview_path=preview_path,
                summary_path=summary_path,
                force=force,
            )
        else:
            summary = _create_placeholder_beam(
                step_path=step_path,
                stl_path=stl_path,
                preview_path=preview_path,
                summary_path=summary_path,
                config=config,
                force=force,
            )

        logger.info(
            "prepare_geometry_artifacts | done | step_path=%s | preview_path=%s",
            summary.step_path,
            summary.preview_path,
        )
        return summary
    except Exception:
        logger.exception(
            "prepare_geometry_artifacts | failed | run_dir=%s | source_step_path=%s | force=%s",
            config.run_dir,
            config.geometry.source_step_path,
            force,
        )
        raise


def render_geometry_preview(step_path: Path, output_path: Path, *, force: bool = False) -> Path:
    """Render a light-weight preview of a STEP solid using tessellation."""

    logger.info("render_geometry_preview | start | step_path=%s | output_path=%s | force=%s", step_path, output_path, force)
    try:
        output_path = Path(output_path)
        if output_path.exists() and not force:
            return output_path
        shape = _import_step_shape(step_path)
        solid = shape.val()
        vertices, triangles = solid.tessellate(_preview_tolerance(solid))
        _plot_tessellated_surface(vertices, triangles, output_path=output_path)
        logger.info("render_geometry_preview | done | output_path=%s", output_path)
        return output_path
    except Exception:
        logger.exception("render_geometry_preview | failed | step_path=%s | output_path=%s", step_path, output_path)
        raise


def load_geometry_summary(step_path: Path, *, source_mode: str, stl_path: Path | None = None, preview_path: Path | None = None) -> GeometrySummary:
    """Collect deterministic geometry metadata from a STEP file."""

    logger.info("load_geometry_summary | start | step_path=%s | source_mode=%s", step_path, source_mode)
    try:
        shape = _import_step_shape(step_path)
        solid = shape.val()
        bbox = solid.BoundingBox()
        bbox_min = (float(bbox.xmin), float(bbox.ymin), float(bbox.zmin))
        bbox_max = (float(bbox.xmax), float(bbox.ymax), float(bbox.zmax))
        spans: tuple[float, float, float] = (
            max(bbox_max[0] - bbox_min[0], 0.0),
            max(bbox_max[1] - bbox_min[1], 0.0),
            max(bbox_max[2] - bbox_min[2], 0.0),
        )
        major_axis = _major_axis(spans)
        summary_path = Path(preview_path).with_name("geometry_summary.json") if preview_path else Path(step_path).with_name("geometry_summary.json")
        summary = GeometrySummary(
            source_mode=source_mode,
            step_path=Path(step_path),
            preview_path=Path(preview_path) if preview_path else Path(step_path).with_name("geometry_preview.png"),
            summary_path=summary_path,
            stl_path=Path(stl_path) if stl_path is not None else None,
            name=Path(step_path).stem,
            face_count=len(solid.Faces()),
            edge_count=len(solid.Edges()),
            solid_count=len(solid.Solids()),
            bbox_min_mm=bbox_min,
            bbox_max_mm=bbox_max,
            spans_mm=spans,
            major_axis=major_axis,
            volume_mm3=float(solid.Volume()),
            surface_area_mm2=float(solid.Area()),
        )
        logger.info(
            "load_geometry_summary | done | step_path=%s | major_axis=%s | spans_mm=%s",
            step_path,
            major_axis,
            spans,
        )
        return summary
    except Exception:
        logger.exception("load_geometry_summary | failed | step_path=%s | source_mode=%s", step_path, source_mode)
        raise


def geometry_summary_to_dict(summary: GeometrySummary) -> dict[str, Any]:
    """Convert a geometry summary into a JSON-friendly dictionary."""

    return {
        "source_mode": summary.source_mode,
        "step_path": str(summary.step_path),
        "preview_path": str(summary.preview_path),
        "summary_path": str(summary.summary_path),
        "stl_path": str(summary.stl_path) if summary.stl_path is not None else None,
        "name": summary.name,
        "face_count": summary.face_count,
        "edge_count": summary.edge_count,
        "solid_count": summary.solid_count,
        "bbox_min_mm": list(summary.bbox_min_mm),
        "bbox_max_mm": list(summary.bbox_max_mm),
        "spans_mm": list(summary.spans_mm),
        "major_axis": summary.major_axis,
        "volume_mm3": summary.volume_mm3,
        "surface_area_mm2": summary.surface_area_mm2,
    }


def _create_placeholder_beam(
    *,
    step_path: Path,
    stl_path: Path,
    preview_path: Path,
    summary_path: Path,
    config: FEAReplicationConfig,
    force: bool,
) -> GeometrySummary:
    """Create a deterministic cantilever beam as the fallback geometry."""

    if not force and (step_path.exists() or stl_path.exists() or preview_path.exists() or summary_path.exists()):
        raise FileExistsError(f"Existing geometry artifacts found in {step_path.parent}. Use force=True to overwrite.")

    beam = (
        cq.Workplane("XY")
        .box(config.geometry.length_mm, config.geometry.width_mm, config.geometry.thickness_mm)
    )
    export_step_and_stl(beam, step_path.parent, step_path.stem, force=True)
    preview_path = render_geometry_preview(step_path, preview_path, force=True)
    summary = load_geometry_summary(step_path, source_mode="generated_placeholder", stl_path=stl_path, preview_path=preview_path)
    write_json(summary_path, geometry_summary_to_dict(summary), force=True)
    return summary


def _copy_existing_step(
    *,
    source_step_path: Path,
    step_path: Path,
    stl_path: Path,
    preview_path: Path,
    summary_path: Path,
    force: bool,
) -> GeometrySummary:
    """Copy a user-provided STEP file into the run directory and summarize it."""

    if not source_step_path.exists():
        raise FileNotFoundError(f"Source STEP file not found: {source_step_path}")
    if not force and (step_path.exists() or stl_path.exists() or preview_path.exists() or summary_path.exists()):
        raise FileExistsError(f"Existing geometry artifacts found in {step_path.parent}. Use force=True to overwrite.")

    if source_step_path.resolve() != step_path.resolve():
        shutil.copy2(source_step_path, step_path)
    shape = _import_step_shape(step_path)
    cq.exporters.export(shape, str(stl_path))
    preview_path = render_geometry_preview(step_path, preview_path, force=True)
    summary = load_geometry_summary(step_path, source_mode="provided_step", stl_path=stl_path, preview_path=preview_path)
    write_json(summary_path, geometry_summary_to_dict(summary), force=True)
    return summary


def _import_step_shape(step_path: Path) -> Any:
    """Import a STEP file as a CadQuery shape."""

    if not Path(step_path).exists():
        raise FileNotFoundError(f"STEP file not found: {step_path}")
    shape = cq.importers.importStep(str(step_path))
    if shape is None:
        raise ValueError(f"Could not import STEP geometry from {step_path}")
    return shape


def _major_axis(spans: tuple[float, float, float]) -> str:
    """Return the longest axis name for a bounding box."""

    axis_names = ("X", "Y", "Z")
    index = int(np.argmax(np.asarray(spans, dtype=float)))
    return axis_names[index]


def _preview_tolerance(solid: Any) -> float:
    """Choose a tessellation tolerance for preview rendering."""

    bbox = solid.BoundingBox()
    span = max(float(bbox.xlen), float(bbox.ylen), float(bbox.zlen), 1.0)
    return max(span / 60.0, 0.5)


def _plot_tessellated_surface(vertices: list[Any], triangles: list[Any], *, output_path: Path) -> None:
    """Render tessellated triangles with matplotlib."""

    points = np.asarray([[float(coord) for coord in point] for point in vertices], dtype=float)
    faces = np.asarray(triangles, dtype=int)
    polys = [points[face] for face in faces]

    fig = plt.figure(figsize=(5.5, 4.5), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    collection = Poly3DCollection(polys, facecolor="#8bb7d6", edgecolor="#355a6e", linewidths=0.25, alpha=0.95)
    ax.add_collection3d(collection)
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = (mins + maxs) / 2.0
    max_span = float(np.max(np.maximum(maxs - mins, 1.0e-6)))
    half_span = max_span * 0.58
    ax.set_xlim(center[0] - half_span, center[0] + half_span)
    ax.set_ylim(center[1] - half_span, center[1] + half_span)
    ax.set_zlim(center[2] - half_span, center[2] + half_span)
    ax.set_box_aspect((1.0, 1.0, 1.0))
    ax.view_init(elev=25.0, azim=-45.0)
    ax.set_axis_off()
    fig.tight_layout(pad=0.2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
