# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/visual_analysis/rendering/comparison_metrics.py
"""
Deterministic metrics for structured CAD render artifacts.

RGB overlays are intentionally excluded from scoring. This module compares only
structured artifacts that share artifact type and view metadata: silhouette,
depth, edge, and slice images.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Tuple

import numpy as np
import pandas as pd
from PIL import Image

try:
    from scipy.ndimage import distance_transform_edt, label as label_components
except Exception:  # pragma: no cover - scipy is available in the CAD env
    distance_transform_edt = None
    label_components = None


ArtifactKey = Tuple[str, str]


def compare_structured_render_artifacts(
    gt_artifacts: Mapping[ArtifactKey, str | Path],
    generated_artifacts: Mapping[ArtifactKey, str | Path],
    *,
    camera_metadata: Mapping[str, Mapping[ArtifactKey, Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Compare matched structured GT/generated render artifacts."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped: list[str] = []

    for artifact_type in ("silhouette", "depth", "edge", "slice"):
        gt_keys = {key for key in gt_artifacts if key[0] == artifact_type}
        gen_keys = {key for key in generated_artifacts if key[0] == artifact_type}
        for key in sorted(gt_keys & gen_keys):
            if camera_metadata and not _camera_metadata_matches(key, camera_metadata):
                skipped.append(f"{artifact_type}:{key[1]} camera mismatch")
                continue
            gt_path = gt_artifacts[key]
            gen_path = generated_artifacts[key]
            if artifact_type == "silhouette":
                grouped[artifact_type].append(_compare_silhouette(gt_path, gen_path, key[1]))
            elif artifact_type == "depth":
                grouped[artifact_type].append(_compare_depth(gt_path, gen_path, key[1]))
            elif artifact_type == "edge":
                grouped[artifact_type].append(_compare_edge(gt_path, gen_path, key[1]))
            elif artifact_type == "slice":
                grouped[artifact_type].append(_compare_slice(gt_path, gen_path, key[1]))

    metrics: dict[str, Any] = {"Visual_Compared_View_Count": int(sum(len(values) for values in grouped.values()))}
    metrics["Visual_Skipped_View_Count"] = len(skipped)
    metrics["Visual_Skipped_Reasons"] = skipped
    metrics.update(_aggregate_silhouette(grouped["silhouette"]))
    metrics.update(_aggregate_depth(grouped["depth"]))
    metrics.update(_aggregate_edge(grouped["edge"]))
    metrics.update(_aggregate_slice(grouped["slice"]))
    metrics.update(_aggregate_visual_scores(metrics))
    return metrics


def compare_render_record_frame(
    records: pd.DataFrame,
    *,
    generated_source_type: str | None = None,
) -> dict[str, Any]:
    """Build artifact dictionaries from cad_rendered_views-style rows and compare them."""
    if records.empty:
        return compare_structured_render_artifacts({}, {})

    frame = records.copy()
    if generated_source_type:
        frame = frame[
            frame["source_type"].isin(["ground_truth", generated_source_type])
        ].copy()

    gt_artifacts: dict[ArtifactKey, Path] = {}
    gen_artifacts: dict[ArtifactKey, Path] = {}
    metadata = {"ground_truth": {}, "generated": {}}
    for _, row in frame.iterrows():
        key = (str(row.get("artifact_type")), str(row.get("view_name")))
        path = row.get("image_path")
        if not path or key[0] == "overlay":
            continue
        source_type = str(row.get("source_type"))
        if source_type == "ground_truth":
            gt_artifacts[key] = Path(path)
            metadata["ground_truth"][key] = row.get("camera_metadata") or {}
        elif source_type.startswith("generated_"):
            gen_artifacts[key] = Path(path)
            metadata["generated"][key] = row.get("camera_metadata") or {}

    return compare_structured_render_artifacts(
        gt_artifacts,
        gen_artifacts,
        camera_metadata=metadata,
    )


def _camera_metadata_matches(
    key: ArtifactKey,
    camera_metadata: Mapping[str, Mapping[ArtifactKey, Mapping[str, Any]]],
) -> bool:
    gt = camera_metadata.get("ground_truth", {}).get(key, {})
    gen = camera_metadata.get("generated", {}).get(key, {})
    if not gt or not gen:
        return True
    comparable_keys = [
        "view_name",
        "view_direction",
        "up_vector",
        "right_vector",
        "projection",
        "render_resolution",
        "slice_axis",
        "slice_offset",
    ]
    for name in comparable_keys:
        if name in gt or name in gen:
            if gt.get(name) != gen.get(name):
                return False
    return True


def _open_rgba(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def _foreground_mask(path: str | Path, *, threshold: int = 245) -> np.ndarray:
    arr = np.asarray(_open_rgba(path))
    alpha = arr[..., 3]
    gray = np.asarray(Image.fromarray(arr).convert("L"))
    if alpha.max() != alpha.min():
        return alpha > 0
    return gray < threshold


def _grayscale_object(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    image = _open_rgba(path)
    gray = np.asarray(image.convert("L"), dtype=float) / 255.0
    mask = _foreground_mask(path)
    return gray, mask


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _compare_silhouette(gt_path: str | Path, gen_path: str | Path, view_name: str) -> dict[str, Any]:
    gt = _foreground_mask(gt_path)
    gen = _foreground_mask(gen_path)
    intersection = float(np.logical_and(gt, gen).sum())
    union = float(np.logical_or(gt, gen).sum())
    gt_area = float(gt.sum())
    gen_area = float(gen.sum())
    missing = float(np.logical_and(gt, ~gen).sum())
    extra = float(np.logical_and(gen, ~gt).sum())
    return {
        "view": view_name,
        "iou": _safe_ratio(intersection, union),
        "precision": _safe_ratio(intersection, gen_area),
        "recall": _safe_ratio(intersection, gt_area),
        "missing_area_ratio": _safe_ratio(missing, gt_area),
        "extra_area_ratio": _safe_ratio(extra, gen_area),
    }


def _compare_depth(gt_path: str | Path, gen_path: str | Path, view_name: str) -> dict[str, Any]:
    gt_depth, gt_mask = _grayscale_object(gt_path)
    gen_depth, gen_mask = _grayscale_object(gen_path)
    mask = np.logical_or(gt_mask, gen_mask)
    if not mask.any():
        return {"view": view_name, "mae": 0.0, "rmse": 0.0, "error_area_ratio": 0.0}
    diff = np.abs(gt_depth - gen_depth)
    active = diff[mask]
    return {
        "view": view_name,
        "mae": float(active.mean()),
        "rmse": float(np.sqrt(np.mean(active**2))),
        "error_area_ratio": float((active > 0.10).mean()),
    }


def _compare_edge(gt_path: str | Path, gen_path: str | Path, view_name: str) -> dict[str, Any]:
    gt = _foreground_mask(gt_path)
    gen = _foreground_mask(gen_path)
    if not gt.any() and not gen.any():
        return {"view": view_name, "chamfer": 0.0, "hausdorff": 0.0}
    if distance_transform_edt is None:
        diff = np.logical_xor(gt, gen).mean()
        return {"view": view_name, "chamfer": float(diff), "hausdorff": float(diff)}
    gt_dist = distance_transform_edt(~gt)
    gen_dist = distance_transform_edt(~gen)
    gt_to_gen = gen_dist[gt]
    gen_to_gt = gt_dist[gen]
    distances = []
    if gt_to_gen.size:
        distances.append(gt_to_gen)
    if gen_to_gt.size:
        distances.append(gen_to_gt)
    if not distances:
        return {"view": view_name, "chamfer": 0.0, "hausdorff": 0.0}
    joined = np.concatenate(distances)
    normalizer = max(gt.shape)
    return {
        "view": view_name,
        "chamfer": float(joined.mean() / normalizer),
        "hausdorff": float(joined.max() / normalizer),
    }


def _compare_slice(gt_path: str | Path, gen_path: str | Path, view_name: str) -> dict[str, Any]:
    gt = _foreground_mask(gt_path)
    gen = _foreground_mask(gen_path)
    intersection = float(np.logical_and(gt, gen).sum())
    union = float(np.logical_or(gt, gen).sum())
    return {
        "view": view_name,
        "iou": _safe_ratio(intersection, union),
        "component_delta": abs(_component_count(gt) - _component_count(gen)),
        "hole_delta": abs(_hole_count(gt) - _hole_count(gen)),
    }


def _component_count(mask: np.ndarray) -> int:
    if not mask.any():
        return 0
    if label_components is None:
        return 1
    _, count = label_components(mask)
    return int(count)


def _hole_count(mask: np.ndarray) -> int:
    if not mask.any() or label_components is None:
        return 0
    ys, xs = np.where(mask)
    y0, y1 = ys.min(), ys.max() + 1
    x0, x1 = xs.min(), xs.max() + 1
    local_bg = ~mask[y0:y1, x0:x1]
    _, count = label_components(local_bg)
    return max(int(count) - 1, 0)


def _aggregate_silhouette(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "Silhouette_IoU_Mean": None,
            "Silhouette_IoU_Min": None,
            "Silhouette_Precision_Mean": None,
            "Silhouette_Recall_Mean": None,
            "Missing_Area_Ratio_Max": None,
            "Extra_Area_Ratio_Max": None,
            "Worst_Silhouette_View": None,
        }
    worst = min(rows, key=lambda row: row["iou"])
    return {
        "Silhouette_IoU_Mean": float(np.mean([row["iou"] for row in rows])),
        "Silhouette_IoU_Min": float(np.min([row["iou"] for row in rows])),
        "Silhouette_Precision_Mean": float(np.mean([row["precision"] for row in rows])),
        "Silhouette_Recall_Mean": float(np.mean([row["recall"] for row in rows])),
        "Missing_Area_Ratio_Max": float(np.max([row["missing_area_ratio"] for row in rows])),
        "Extra_Area_Ratio_Max": float(np.max([row["extra_area_ratio"] for row in rows])),
        "Worst_Silhouette_View": worst["view"],
    }


def _aggregate_depth(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "Depth_MAE_Mean": None,
            "Depth_RMSE_Mean": None,
            "Depth_Error_Area_Ratio_Max": None,
            "Worst_Depth_View": None,
        }
    worst = max(rows, key=lambda row: row["rmse"])
    return {
        "Depth_MAE_Mean": float(np.mean([row["mae"] for row in rows])),
        "Depth_RMSE_Mean": float(np.mean([row["rmse"] for row in rows])),
        "Depth_Error_Area_Ratio_Max": float(np.max([row["error_area_ratio"] for row in rows])),
        "Worst_Depth_View": worst["view"],
    }


def _aggregate_edge(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "Edge_Chamfer_Mean": None,
            "Edge_Hausdorff_Max": None,
            "Worst_Edge_View": None,
        }
    worst = max(rows, key=lambda row: row["hausdorff"])
    return {
        "Edge_Chamfer_Mean": float(np.mean([row["chamfer"] for row in rows])),
        "Edge_Hausdorff_Max": float(np.max([row["hausdorff"] for row in rows])),
        "Worst_Edge_View": worst["view"],
    }


def _aggregate_slice(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "Slice_IoU_Mean": None,
            "Slice_IoU_Min": None,
            "Slice_Component_Delta_Max": None,
            "Slice_Hole_Delta_Max": None,
        }
    return {
        "Slice_IoU_Mean": float(np.mean([row["iou"] for row in rows])),
        "Slice_IoU_Min": float(np.min([row["iou"] for row in rows])),
        "Slice_Component_Delta_Max": int(np.max([row["component_delta"] for row in rows])),
        "Slice_Hole_Delta_Max": int(np.max([row["hole_delta"] for row in rows])),
    }


def _optional_float(metrics: Mapping[str, Any], key: str, default: float) -> float:
    value = metrics.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _aggregate_visual_scores(metrics: Mapping[str, Any]) -> dict[str, float | None]:
    if metrics.get("Visual_Compared_View_Count", 0) == 0:
        return {
            "Visual_Match_Score": None,
            "Visual_Global_Error_Score": None,
            "Visual_Local_Error_Score": None,
            "Visual_Topology_Evidence_Score": None,
        }
    silhouette = _optional_float(metrics, "Silhouette_IoU_Mean", 1.0)
    depth_error = _optional_float(metrics, "Depth_RMSE_Mean", 0.0)
    edge_error = _optional_float(metrics, "Edge_Chamfer_Mean", 0.0)
    slice_iou = _optional_float(metrics, "Slice_IoU_Mean", silhouette)
    match = float(np.clip(np.mean([silhouette, 1.0 - depth_error, 1.0 - edge_error, slice_iou]), 0.0, 1.0))
    local_error = float(
        np.clip(
            max(
                _optional_float(metrics, "Missing_Area_Ratio_Max", 0.0),
                _optional_float(metrics, "Extra_Area_Ratio_Max", 0.0),
                _optional_float(metrics, "Edge_Hausdorff_Max", 0.0),
            ),
            0.0,
            1.0,
        )
    )
    topology = float(
        np.clip(
            (1.0 - slice_iou)
            + 0.10 * _optional_float(metrics, "Slice_Component_Delta_Max", 0.0)
            + 0.10 * _optional_float(metrics, "Slice_Hole_Delta_Max", 0.0),
            0.0,
            1.0,
        )
    )
    return {
        "Visual_Match_Score": match,
        "Visual_Global_Error_Score": float(np.clip(1.0 - np.mean([silhouette, slice_iou]), 0.0, 1.0)),
        "Visual_Local_Error_Score": local_error,
        "Visual_Topology_Evidence_Score": topology,
    }
