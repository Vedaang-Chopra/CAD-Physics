"""Render standard PNG views for a single STL file."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

logger = logging.getLogger(__name__)

_VIEW_SETTINGS: dict[str, dict[str, float]] = {
    "front": {"elev": 0.0, "azim": -90.0},
    "side": {"elev": 0.0, "azim": 0.0},
    "top": {"elev": 90.0, "azim": -90.0},
    "iso": {"elev": 30.0, "azim": -45.0},
}


def render_views(stl_path: Path, output_dir: Path, force: bool = False) -> dict[str, str]:
    """Render front, side, top, and isometric PNG views for one STL."""

    logger.info(
        "render_views | start | stl_path=%s | output_dir=%s | force=%s",
        stl_path,
        output_dir,
        force,
    )
    try:
        stl_path = Path(stl_path)
        output_dir = Path(output_dir)
        _ensure_can_write_views(output_dir, force=force)
        mesh = _load_mesh(stl_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        result: dict[str, str] = {}
        for view_name in ("front", "side", "top", "iso"):
            image_path = output_dir / f"{view_name}.png"
            _render_single_view(mesh, view_name=view_name, output_path=image_path, force=force)
            result[view_name] = str(image_path)

        logger.info(
            "render_views | done | stl_path=%s | output_dir=%s | views=%s",
            stl_path,
            output_dir,
            sorted(result.keys()),
        )
        return result
    except Exception:
        logger.exception(
            "render_views | failed | stl_path=%s | output_dir=%s | force=%s",
            stl_path,
            output_dir,
            force,
        )
        raise


def _ensure_can_write_views(output_dir: Path, *, force: bool) -> None:
    """Refuse to overwrite existing render outputs unless force is enabled."""

    if force:
        return
    existing = [output_dir / f"{view_name}.png" for view_name in _VIEW_SETTINGS]
    if any(path.exists() for path in existing):
        raise FileExistsError(f"Existing render outputs found in {output_dir}. Use force=True to overwrite.")


def _load_mesh(stl_path: Path) -> trimesh.Trimesh:
    """Load and normalize a trimesh mesh from an STL file."""

    if not stl_path.exists():
        raise FileNotFoundError(f"STL file not found: {stl_path}")
    mesh = trimesh.load_mesh(str(stl_path), force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"Expected a Trimesh from {stl_path}, got {type(mesh).__name__}.")
    if mesh.is_empty:
        raise ValueError(f"STL file contains no geometry: {stl_path}")
    mesh = mesh.copy()
    mesh.remove_unreferenced_vertices()
    mesh.apply_translation(-mesh.centroid)
    return mesh


def _render_single_view(mesh: trimesh.Trimesh, *, view_name: str, output_path: Path, force: bool) -> None:
    """Render one standard view to a PNG file."""

    if output_path.exists() and not force:
        return

    triangles = np.asarray(mesh.triangles)
    fig = plt.figure(figsize=(4.0, 4.0), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    collection = Poly3DCollection(
        triangles,
        facecolor="#8bb7d6",
        edgecolor="#34515e",
        linewidths=0.25,
        alpha=1.0,
    )
    ax.add_collection3d(collection)

    points = np.asarray(mesh.vertices, dtype=float)
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    spans = np.maximum(maxs - mins, 1.0e-6)
    center = (mins + maxs) / 2.0
    max_span = float(np.max(spans))
    half_span = max_span * 0.55
    ax.set_xlim(center[0] - half_span, center[0] + half_span)
    ax.set_ylim(center[1] - half_span, center[1] + half_span)
    ax.set_zlim(center[2] - half_span, center[2] + half_span)
    ax.set_box_aspect((1.0, 1.0, 1.0))
    ax.view_init(
        elev=_VIEW_SETTINGS[view_name]["elev"],
        azim=_VIEW_SETTINGS[view_name]["azim"],
    )
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.0)
    plt.close(fig)
