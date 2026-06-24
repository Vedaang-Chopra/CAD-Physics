# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/visual_analysis/rendering/pointcloud_loader.py
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import trimesh


EPSILON = 1.0e-12


@dataclass(frozen=True)
class PointCloudArtifact:
    points: np.ndarray
    source_stl_hash: str
    cached_path: Optional[Path]
    point_count: int


@dataclass(frozen=True)
class NormalizationFrame:
    """Shared geometry frame used to render GT and generated meshes consistently."""

    center: np.ndarray
    scale: float

    def to_metadata(self) -> dict:
        return {
            "center": [float(value) for value in self.center.tolist()],
            "scale": float(self.scale),
            "strategy": "shared_bounds_unit_extent",
        }


def load_mesh_from_stl_bytes(stl_content: bytes) -> trimesh.Trimesh:
    if not stl_content:
        raise ValueError("STL content is empty.")

    loaded = trimesh.load(
        io.BytesIO(stl_content),
        file_type="stl",
        force="mesh",
        process=False,
        maintain_order=True,
    )
    if isinstance(loaded, trimesh.Scene):
        meshes = [geom for geom in loaded.geometry.values() if isinstance(geom, trimesh.Trimesh)]
        if not meshes:
            raise ValueError("STL scene contains no mesh geometry.")
        mesh = trimesh.util.concatenate(meshes)
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        raise ValueError(f"Unsupported STL payload type: {type(loaded)!r}.")

    mesh = mesh.copy()
    mesh.remove_unreferenced_vertices()
    if mesh.vertices is None or len(mesh.vertices) == 0:
        raise ValueError("mesh has no vertices.")
    if mesh.faces is None or len(mesh.faces) == 0:
        raise ValueError("mesh has no triangles.")
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("mesh has non-finite vertices.")
    extents = np.asarray(mesh.bounding_box.extents, dtype=float)
    if extents.size != 3 or float(extents.max()) <= EPSILON:
        raise ValueError("mesh is degenerate.")
    if float(mesh.area) <= EPSILON:
        raise ValueError("mesh has zero surface area.")
    return mesh


def normalize_points(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"point cloud must have shape (N, 3), got {points.shape}.")
    if len(points) == 0:
        raise ValueError("point cloud is empty.")
    if not np.isfinite(points).all():
        raise ValueError("point cloud has non-finite coordinates.")

    centroid = points.mean(axis=0)
    centered = points - centroid
    scale = float(np.linalg.norm(centered, axis=1).max())
    if scale <= EPSILON:
        raise ValueError("point cloud is degenerate after centering.")
    return centered / scale


def build_normalization_frame(meshes: Iterable[trimesh.Trimesh]) -> NormalizationFrame:
    vertices = [
        np.asarray(mesh.vertices, dtype=float)
        for mesh in meshes
        if mesh is not None and len(mesh.vertices) > 0
    ]
    if not vertices:
        raise ValueError("cannot build normalization frame without mesh vertices.")

    merged = np.vstack(vertices)
    if not np.isfinite(merged).all():
        raise ValueError("normalization frame input contains non-finite vertices.")

    mins = merged.min(axis=0)
    maxs = merged.max(axis=0)
    center = (mins + maxs) / 2.0
    scale = float(np.max(maxs - mins))
    if scale <= EPSILON:
        raise ValueError("normalization frame is degenerate.")
    return NormalizationFrame(center=center, scale=scale)


def normalize_mesh(mesh: trimesh.Trimesh, frame: NormalizationFrame) -> trimesh.Trimesh:
    normalized = mesh.copy()
    normalized.vertices = (np.asarray(normalized.vertices, dtype=float) - frame.center) / frame.scale
    normalized.remove_unreferenced_vertices()
    return normalized


def stable_seed_from_hash(source_stl_hash: str) -> int:
    return int(str(source_stl_hash)[:8], 16) if source_stl_hash else 0


def point_cloud_from_stl(
    *,
    stl_content: bytes,
    source_stl_hash: str,
    sample_count: int,
    cache_dir: Path,
) -> PointCloudArtifact:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{source_stl_hash}_{sample_count}.npy"
    if cache_path.exists():
        points = np.load(cache_path)
        return PointCloudArtifact(
            points=points,
            source_stl_hash=source_stl_hash,
            cached_path=cache_path,
            point_count=int(len(points)),
        )

    mesh = load_mesh_from_stl_bytes(stl_content)
    points, _ = trimesh.sample.sample_surface(
        mesh,
        sample_count,
        seed=stable_seed_from_hash(source_stl_hash),
    )
    normalized_points = normalize_points(points)
    np.save(cache_path, normalized_points)
    return PointCloudArtifact(
        points=normalized_points,
        source_stl_hash=source_stl_hash,
        cached_path=cache_path,
        point_count=int(len(normalized_points)),
    )
