# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/visual_analysis/rendering/renderer.py
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageChops, ImageDraw
import trimesh


STANDARD_VIEWS: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = {
    "front": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "back": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "left": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "right": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "top": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    "bottom": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    "isometric": ((1.0, -1.0, 1.0), (0.0, 0.0, 1.0)),
    "isometric_1": ((1.0, -1.0, 1.0), (0.0, 0.0, 1.0)),
    "isometric_2": ((-1.0, -1.0, 0.85), (0.0, 0.0, 1.0)),
    "isometric_3": ((1.0, 1.0, 0.85), (0.0, 0.0, 1.0)),
}

SLICE_VIEWS: Dict[str, Tuple[int, float]] = {
    "slice_xy_25": (2, -0.25),
    "slice_xy_mid": (2, 0.0),
    "slice_xy_75": (2, 0.25),
    "slice_yz_25": (0, -0.25),
    "slice_yz_mid": (0, 0.0),
    "slice_yz_75": (0, 0.25),
    "slice_xz_25": (1, -0.25),
    "slice_xz_mid": (1, 0.0),
    "slice_xz_75": (1, 0.25),
}

MESH_ARTIFACT_TYPES = {"shaded", "silhouette", "depth", "normal", "edge"}
COMPARISON_ARTIFACT_TYPES = {"overlay", "silhouette_diff", "depth_diff", "edge_diff"}
_DEPTH_RANGE = (-1.0, 1.0)


@dataclass(frozen=True)
class RenderedView:
    view_name: str
    image_path: Path
    camera_metadata: Dict[str, object]
    created: bool
    status: str
    artifact_type: str = "pointcloud_debug"
    error_message: Optional[str] = None


def _unit(vector: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(vector), dtype=float)
    norm = float(np.linalg.norm(arr))
    if norm <= 1.0e-12:
        raise ValueError("camera vector has zero length.")
    return arr / norm


def random_camera_direction(index: int, *, seed: int) -> Tuple[float, float, float]:
    rng = np.random.default_rng(seed + index)
    z = float(rng.uniform(-0.85, 0.85))
    theta = float(rng.uniform(0.0, 2.0 * math.pi))
    radius = math.sqrt(max(0.0, 1.0 - z * z))
    return (radius * math.cos(theta), radius * math.sin(theta), z)


def camera_for_view(view_name: str, *, random_seed: int = 0, resolution: Optional[int] = None) -> Dict[str, object]:
    if view_name.startswith("random_"):
        try:
            index = int(view_name.split("_", 1)[1])
        except Exception:
            index = 1
        direction = random_camera_direction(index, seed=random_seed)
        up_hint = (0.0, 0.0, 1.0)
    elif view_name in STANDARD_VIEWS:
        direction, up_hint = STANDARD_VIEWS[view_name]
    else:
        raise ValueError(f"Unsupported view_name: {view_name}")

    view_dir = _unit(direction)
    up = _unit(up_hint)
    if abs(float(np.dot(view_dir, up))) > 0.98:
        up = _unit((0.0, 1.0, 0.0))
    right = _unit(np.cross(up, view_dir))
    up = _unit(np.cross(view_dir, right))
    distance = 2.5

    metadata: Dict[str, object] = {
        "view_name": view_name,
        "camera_position": (view_dir * distance).round(8).tolist(),
        "camera_target": [0.0, 0.0, 0.0],
        "view_direction": view_dir.round(8).tolist(),
        "up_vector": up.round(8).tolist(),
        "right_vector": right.round(8).tolist(),
        "zoom": 1.0,
        "distance": distance,
        "projection": "orthographic",
        "depth_range": list(_DEPTH_RANGE),
    }
    if resolution is not None:
        metadata["render_resolution"] = [resolution, resolution]
    return metadata


def _project_vertices(vertices: np.ndarray, camera_metadata: Mapping[str, object]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    right = np.asarray(camera_metadata["right_vector"], dtype=float)
    up = np.asarray(camera_metadata["up_vector"], dtype=float)
    view_dir = np.asarray(camera_metadata["view_direction"], dtype=float)
    x = vertices @ right
    y = vertices @ up
    depth = vertices @ view_dir
    return x, y, depth


def _to_pixels(x: np.ndarray, y: np.ndarray, resolution: int) -> Tuple[np.ndarray, np.ndarray]:
    fit_extent = 0.62
    px = (x / fit_extent + 1.0) * 0.5 * (resolution - 1)
    py = (1.0 - (y / fit_extent + 1.0) * 0.5) * (resolution - 1)
    return px, py


def render_mesh_artifacts(
    mesh: trimesh.Trimesh,
    *,
    view_name: str,
    output_dir: Path,
    artifact_types: Iterable[str],
    resolution: int,
    background: str,
    random_seed: int = 0,
    overwrite: bool = False,
) -> List[RenderedView]:
    camera_metadata = camera_for_view(view_name, random_seed=random_seed, resolution=resolution)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_types = [artifact_type for artifact_type in artifact_types if artifact_type in MESH_ARTIFACT_TYPES]
    pending = {
        artifact_type: output_dir / artifact_type / f"{view_name}.png"
        for artifact_type in artifact_types
    }
    rendered: List[RenderedView] = []
    for artifact_type, image_path in pending.items():
        if image_path.exists() and not overwrite:
            rendered.append(
                RenderedView(
                    view_name=view_name,
                    image_path=image_path,
                    camera_metadata={**camera_metadata, "artifact_type": artifact_type},
                    created=False,
                    status="skipped_existing",
                    artifact_type=artifact_type,
                )
            )

    pending = {
        artifact_type: image_path
        for artifact_type, image_path in pending.items()
        if overwrite or not image_path.exists()
    }
    if not pending:
        return rendered

    buffers = _rasterize_mesh(mesh, camera_metadata, resolution=resolution)
    images = _images_from_buffers(buffers, artifact_types=pending.keys(), background=background)
    for artifact_type, image_path in pending.items():
        image_path.parent.mkdir(parents=True, exist_ok=True)
        images[artifact_type].save(image_path)
        rendered.append(
            RenderedView(
                view_name=view_name,
                image_path=image_path,
                camera_metadata={**camera_metadata, "artifact_type": artifact_type},
                created=True,
                status="success",
                artifact_type=artifact_type,
            )
        )
    return rendered


def render_slice_view(
    mesh: trimesh.Trimesh,
    *,
    slice_view_name: str,
    image_path: Path,
    resolution: int,
    background: str,
    overwrite: bool = False,
) -> RenderedView:
    axis, offset = SLICE_VIEWS[slice_view_name]
    metadata = {
        "view_name": slice_view_name,
        "slice_axis": ["x", "y", "z"][axis],
        "slice_offset_normalized": offset,
        "render_resolution": [resolution, resolution],
        "slice_strategy": "triangle_plane_intersection",
        "artifact_type": "slice",
    }
    if image_path.exists() and not overwrite:
        return RenderedView(
            view_name=slice_view_name,
            image_path=image_path,
            camera_metadata=metadata,
            created=False,
            status="skipped_existing",
            artifact_type="slice",
        )

    image_path.parent.mkdir(parents=True, exist_ok=True)
    segments = _slice_segments(mesh, axis=axis, offset=offset)
    image = _draw_slice_segments(
        segments,
        axis=axis,
        resolution=resolution,
        background=(255, 255, 255, 0) if background == "transparent" else (255, 255, 255, 255),
    )
    image.save(image_path)
    return RenderedView(
        view_name=slice_view_name,
        image_path=image_path,
        camera_metadata=metadata,
        created=True,
        status="success",
        artifact_type="slice",
    )


def render_point_cloud_view(
    points: np.ndarray,
    *,
    view_name: str,
    image_path: Path,
    resolution: int,
    background: str,
    point_size: float,
    random_seed: int = 0,
    overwrite: bool = False,
) -> RenderedView:
    camera_metadata = camera_for_view(view_name, random_seed=random_seed, resolution=resolution)
    camera_metadata["artifact_type"] = "pointcloud_debug"

    if image_path.exists() and not overwrite:
        return RenderedView(
            view_name=view_name,
            image_path=image_path,
            camera_metadata=camera_metadata,
            created=False,
            status="skipped_existing",
            artifact_type="pointcloud_debug",
        )

    image_path.parent.mkdir(parents=True, exist_ok=True)
    x, y, depth = _project_vertices(points, camera_metadata)
    order = np.argsort(depth)

    transparent = background == "transparent"
    facecolor = "none" if transparent else "white"
    fig = plt.figure(figsize=(resolution / 100.0, resolution / 100.0), dpi=100, facecolor=facecolor)
    ax = fig.add_axes([0, 0, 1, 1], facecolor=facecolor)
    depth_min = float(np.min(depth)) if len(depth) else 0.0
    depth_span = float(np.max(depth) - depth_min) if len(depth) else 1.0
    normalized_depth = (depth[order] - depth_min) / max(depth_span, 1.0e-12)
    colors = plt.cm.Greys(0.35 + 0.55 * normalized_depth)
    ax.scatter(x[order], y[order], c=colors, s=point_size, linewidths=0, alpha=0.96)
    ax.set_xlim(-0.62, 0.62)
    ax.set_ylim(-0.62, 0.62)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(image_path, dpi=100, transparent=transparent, facecolor=facecolor)
    plt.close(fig)

    with Image.open(image_path) as img:
        if img.size != (resolution, resolution):
            img = img.resize((resolution, resolution))
            img.save(image_path)

    return RenderedView(
        view_name=view_name,
        image_path=image_path,
        camera_metadata=camera_metadata,
        created=True,
        status="success",
        artifact_type="pointcloud_debug",
    )


def render_comparison_artifact(
    *,
    gt_artifacts: Mapping[Tuple[str, str], Path],
    generated_artifacts: Mapping[Tuple[str, str], Path],
    artifact_type: str,
    view_name: str,
    image_path: Path,
    resolution: int,
    overwrite: bool = False,
) -> RenderedView:
    metadata = {
        "view_name": view_name,
        "artifact_type": artifact_type,
        "render_resolution": [resolution, resolution],
        "comparison_inputs": {
            "ground_truth": str(_comparison_input_path(gt_artifacts, artifact_type, view_name)),
            "generated": str(_comparison_input_path(generated_artifacts, artifact_type, view_name)),
        },
    }
    if image_path.exists() and not overwrite:
        return RenderedView(
            view_name=view_name,
            image_path=image_path,
            camera_metadata=metadata,
            created=False,
            status="skipped_existing",
            artifact_type=artifact_type,
        )

    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = _build_comparison_image(
        gt_artifacts=gt_artifacts,
        generated_artifacts=generated_artifacts,
        artifact_type=artifact_type,
        view_name=view_name,
        resolution=resolution,
    )
    image.save(image_path)
    return RenderedView(
        view_name=view_name,
        image_path=image_path,
        camera_metadata=metadata,
        created=True,
        status="success",
        artifact_type=artifact_type,
    )


def _rasterize_mesh(mesh: trimesh.Trimesh, camera_metadata: Mapping[str, object], *, resolution: int) -> Dict[str, np.ndarray]:
    vertices = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=int)
    face_normals = np.asarray(mesh.face_normals, dtype=float)
    x, y, depth = _project_vertices(vertices, camera_metadata)
    px, py = _to_pixels(x, y, resolution)

    z_buffer = np.full((resolution, resolution), -np.inf, dtype=float)
    face_buffer = np.full((resolution, resolution), -1, dtype=int)
    bary_buffer = np.zeros((resolution, resolution, 3), dtype=float)

    face_depth = depth[faces].mean(axis=1)
    for face_index in np.argsort(face_depth):
        tri = faces[face_index]
        tri_x = px[tri]
        tri_y = py[tri]
        tri_z = depth[tri]
        min_x = max(int(np.floor(np.min(tri_x))), 0)
        max_x = min(int(np.ceil(np.max(tri_x))), resolution - 1)
        min_y = max(int(np.floor(np.min(tri_y))), 0)
        max_y = min(int(np.ceil(np.max(tri_y))), resolution - 1)
        if min_x > max_x or min_y > max_y:
            continue

        xs, ys = np.meshgrid(
            np.arange(min_x, max_x + 1, dtype=float) + 0.5,
            np.arange(min_y, max_y + 1, dtype=float) + 0.5,
        )
        bary = _barycentric(xs, ys, tri_x, tri_y)
        inside = np.all(bary >= -1.0e-8, axis=-1)
        if not np.any(inside):
            continue
        z = bary[..., 0] * tri_z[0] + bary[..., 1] * tri_z[1] + bary[..., 2] * tri_z[2]
        patch = z_buffer[min_y : max_y + 1, min_x : max_x + 1]
        update = inside & (z > patch)
        if not np.any(update):
            continue
        patch[update] = z[update]
        face_patch = face_buffer[min_y : max_y + 1, min_x : max_x + 1]
        face_patch[update] = face_index
        bary_patch = bary_buffer[min_y : max_y + 1, min_x : max_x + 1]
        bary_patch[update] = bary[update]

    return {
        "z_buffer": z_buffer,
        "face_buffer": face_buffer,
        "face_normals": face_normals,
        "px": px,
        "py": py,
        "faces": faces,
        "mask": face_buffer >= 0,
    }


def _barycentric(xs: np.ndarray, ys: np.ndarray, tri_x: np.ndarray, tri_y: np.ndarray) -> np.ndarray:
    x0, x1, x2 = tri_x
    y0, y1, y2 = tri_y
    denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(float(denom)) <= 1.0e-12:
        return np.full((*xs.shape, 3), -1.0, dtype=float)
    w0 = ((y1 - y2) * (xs - x2) + (x2 - x1) * (ys - y2)) / denom
    w1 = ((y2 - y0) * (xs - x2) + (x0 - x2) * (ys - y2)) / denom
    w2 = 1.0 - w0 - w1
    return np.stack([w0, w1, w2], axis=-1)


def _images_from_buffers(
    buffers: Mapping[str, np.ndarray],
    *,
    artifact_types: Iterable[str],
    background: str,
) -> Dict[str, Image.Image]:
    mask = buffers["mask"]
    face_buffer = buffers["face_buffer"]
    z_buffer = buffers["z_buffer"]
    normals = buffers["face_normals"]
    height, width = mask.shape
    bg = np.array([255, 255, 255, 0 if background == "transparent" else 255], dtype=np.uint8)
    rgb_base = np.tile(bg, (height, width, 1))
    images: Dict[str, Image.Image] = {}

    if "shaded" in artifact_types:
        light = _unit((0.45, -0.55, 0.75))
        pixel_normals = np.zeros((height, width, 3), dtype=float)
        pixel_normals[mask] = normals[np.maximum(face_buffer[mask], 0)]
        diffuse = np.clip(pixel_normals @ light, 0.0, 1.0)
        shade = 0.36 + 0.55 * diffuse
        color = rgb_base.copy()
        base_color = np.array([92, 126, 171], dtype=float)
        color[mask, :3] = np.clip(base_color * shade[mask, None] + 28, 0, 255).astype(np.uint8)
        color[mask, 3] = 255
        images["shaded"] = Image.fromarray(color, mode="RGBA")

    if "silhouette" in artifact_types:
        color = rgb_base.copy()
        color[mask, :3] = 0
        color[mask, 3] = 255
        images["silhouette"] = Image.fromarray(color, mode="RGBA")

    if "depth" in artifact_types:
        depth_min, depth_max = _DEPTH_RANGE
        depth_norm = np.clip((z_buffer - depth_min) / (depth_max - depth_min), 0.0, 1.0)
        color = rgb_base.copy()
        color[mask, :3] = (255 - depth_norm[mask, None] * 210).astype(np.uint8)
        color[mask, 3] = 255
        images["depth"] = Image.fromarray(color, mode="RGBA")

    if "normal" in artifact_types:
        color = rgb_base.copy()
        pixel_normals = np.zeros((height, width, 3), dtype=float)
        pixel_normals[mask] = normals[np.maximum(face_buffer[mask], 0)]
        color[mask, :3] = np.clip((pixel_normals[mask] * 0.5 + 0.5) * 255, 0, 255).astype(np.uint8)
        color[mask, 3] = 255
        images["normal"] = Image.fromarray(color, mode="RGBA")

    if "edge" in artifact_types:
        images["edge"] = _edge_image(
            mask,
            background=background,
            px=buffers.get("px"),
            py=buffers.get("py"),
            faces=buffers.get("faces"),
        )

    return images


def _edge_image(
    mask: np.ndarray,
    *,
    background: str,
    px: Optional[np.ndarray] = None,
    py: Optional[np.ndarray] = None,
    faces: Optional[np.ndarray] = None,
) -> Image.Image:
    bg = (255, 255, 255, 0 if background == "transparent" else 255)
    image = Image.new("RGBA", (mask.shape[1], mask.shape[0]), bg)
    edges = np.zeros(mask.shape, dtype=bool)
    edges[1:, :] |= mask[1:, :] != mask[:-1, :]
    edges[:-1, :] |= mask[:-1, :] != mask[1:, :]
    edges[:, 1:] |= mask[:, 1:] != mask[:, :-1]
    edges[:, :-1] |= mask[:, :-1] != mask[:, 1:]
    arr = np.asarray(image).copy()
    arr[mask, :3] = 232
    arr[mask, 3] = 255
    arr[edges, :3] = 15
    arr[edges, 3] = 255
    image = Image.fromarray(arr, mode="RGBA")
    if px is not None and py is not None and faces is not None:
        draw = ImageDraw.Draw(image)
        drawn_edges = set()
        width = max(1, mask.shape[0] // 384)
        for face in faces:
            for start, end in (
                (int(face[0]), int(face[1])),
                (int(face[1]), int(face[2])),
                (int(face[2]), int(face[0])),
            ):
                key = tuple(sorted((start, end)))
                if key in drawn_edges:
                    continue
                drawn_edges.add(key)
                draw.line(
                    [(float(px[start]), float(py[start])), (float(px[end]), float(py[end]))],
                    fill=(24, 24, 24, 210),
                    width=width,
                )
    return image


def _slice_segments(mesh: trimesh.Trimesh, *, axis: int, offset: float) -> List[np.ndarray]:
    vertices = np.asarray(mesh.vertices, dtype=float)
    segments: List[np.ndarray] = []
    for face in np.asarray(mesh.faces, dtype=int):
        tri = vertices[face]
        distances = tri[:, axis] - offset
        points: List[np.ndarray] = []
        for start, end in ((0, 1), (1, 2), (2, 0)):
            d0 = distances[start]
            d1 = distances[end]
            p0 = tri[start]
            p1 = tri[end]
            if abs(float(d0)) <= 1.0e-9:
                points.append(p0)
            if d0 * d1 < 0.0:
                t = abs(float(d0)) / (abs(float(d0)) + abs(float(d1)))
                points.append(p0 + t * (p1 - p0))
        unique: List[np.ndarray] = []
        for point in points:
            if not any(np.linalg.norm(point - existing) <= 1.0e-8 for existing in unique):
                unique.append(point)
        if len(unique) >= 2:
            segments.append(np.vstack(unique[:2]))
    return segments


def _draw_slice_segments(
    segments: List[np.ndarray],
    *,
    axis: int,
    resolution: int,
    background: Tuple[int, int, int, int],
) -> Image.Image:
    image = Image.new("RGBA", (resolution, resolution), background)
    draw = ImageDraw.Draw(image)
    if not segments:
        return image
    axes = [idx for idx in range(3) if idx != axis]
    fit_extent = 0.62

    def to_px(point: np.ndarray) -> Tuple[int, int]:
        x = float(point[axes[0]])
        y = float(point[axes[1]])
        px = int(round((x / fit_extent + 1.0) * 0.5 * (resolution - 1)))
        py = int(round((1.0 - (y / fit_extent + 1.0) * 0.5) * (resolution - 1)))
        return px, py

    for segment in segments:
        draw.line([to_px(segment[0]), to_px(segment[1])], fill=(20, 20, 20, 255), width=max(1, resolution // 256))
    return image


def _comparison_input_path(
    artifacts: Mapping[Tuple[str, str], Path],
    artifact_type: str,
    view_name: str,
) -> Optional[Path]:
    source_type = _comparison_source_artifact_type(artifact_type)
    return artifacts.get((source_type, view_name))


def _comparison_source_artifact_type(artifact_type: str) -> str:
    if artifact_type == "overlay":
        return "shaded"
    if artifact_type == "silhouette_diff":
        return "silhouette"
    if artifact_type == "depth_diff":
        return "depth"
    if artifact_type == "edge_diff":
        return "edge"
    raise ValueError(f"unsupported comparison artifact type: {artifact_type}")


def _open_rgba(path: Optional[Path], *, resolution: int) -> Image.Image:
    if path is None or not path.exists():
        return Image.new("RGBA", (resolution, resolution), (255, 255, 255, 255))
    with Image.open(path) as image:
        return image.convert("RGBA").resize((resolution, resolution))


def _build_comparison_image(
    *,
    gt_artifacts: Mapping[Tuple[str, str], Path],
    generated_artifacts: Mapping[Tuple[str, str], Path],
    artifact_type: str,
    view_name: str,
    resolution: int,
) -> Image.Image:
    source_artifact_type = _comparison_source_artifact_type(artifact_type)
    gt = _open_rgba(gt_artifacts.get((source_artifact_type, view_name)), resolution=resolution)
    generated = _open_rgba(generated_artifacts.get((source_artifact_type, view_name)), resolution=resolution)

    if artifact_type == "overlay":
        gt_arr = np.asarray(gt).copy()
        gen_arr = np.asarray(generated).copy()
        gt_mask = np.asarray(gt.convert("L")) < 250
        gen_mask = np.asarray(generated.convert("L")) < 250
        out = np.full((resolution, resolution, 4), 255, dtype=np.uint8)
        out[gt_mask, :3] = np.array([52, 104, 175], dtype=np.uint8)
        out[gt_mask, 3] = 210
        out[gen_mask, :3] = np.array([215, 75, 65], dtype=np.uint8)
        out[gen_mask, 3] = 210
        both = gt_mask & gen_mask
        out[both, :3] = ((gt_arr[both, :3].astype(int) + gen_arr[both, :3].astype(int)) / 2).astype(np.uint8)
        out[both, 3] = 255
        return Image.fromarray(out, mode="RGBA")

    if artifact_type in {"silhouette_diff", "edge_diff"}:
        diff = ImageChops.difference(gt.convert("L"), generated.convert("L"))
        arr = np.asarray(diff)
        out = np.full((resolution, resolution, 4), 255, dtype=np.uint8)
        out[arr > 24, :3] = np.array([220, 38, 38], dtype=np.uint8)
        out[arr > 24, 3] = 255
        return Image.fromarray(out, mode="RGBA")

    if artifact_type == "depth_diff":
        diff = ImageChops.difference(gt.convert("L"), generated.convert("L"))
        arr = np.asarray(diff, dtype=float) / 255.0
        out = np.full((resolution, resolution, 4), 255, dtype=np.uint8)
        out[:, :, 0] = np.clip(255, 0, 255)
        out[:, :, 1] = np.clip(255 - arr * 210, 0, 255).astype(np.uint8)
        out[:, :, 2] = np.clip(255 - arr * 210, 0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return Image.fromarray(out, mode="RGBA")

    raise ValueError(f"unsupported comparison artifact type: {artifact_type}")
