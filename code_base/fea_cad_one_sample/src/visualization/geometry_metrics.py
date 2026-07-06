"""Deterministic geometry metrics for State A/B/C STL comparisons."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import trimesh

logger = logging.getLogger(__name__)


def compute_geometry_metrics(
    state_paths: Mapping[str, Path],
    output_path: Path,
    force: bool = False,
) -> dict[str, Any]:
    """Compute deterministic geometry metrics and write them to JSON."""

    logger.info(
        "compute_geometry_metrics | start | state_labels=%s | output_path=%s | force=%s",
        list(state_paths.keys()),
        output_path,
        force,
    )
    try:
        output_path = Path(output_path)
        _ensure_can_write(output_path, force=force)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        states: dict[str, dict[str, Any]] = {}
        ordered_labels = list(state_paths.keys())
        for label in ordered_labels:
            states[label] = _measure_state(Path(state_paths[label]))

        pairwise_deltas = _measure_pairwise_deltas(states, ordered_labels)
        payload = {
            "sample_id": _infer_sample_id(output_path),
            "state_order": ordered_labels,
            "states": states,
            "pairwise_deltas": pairwise_deltas,
        }
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        logger.info(
            "compute_geometry_metrics | done | output_path=%s | state_count=%d",
            output_path,
            len(states),
        )
        return payload
    except Exception:
        logger.exception(
            "compute_geometry_metrics | failed | output_path=%s | force=%s",
            output_path,
            force,
        )
        raise


def load_geometry_metrics(output_path: Path) -> dict[str, Any]:
    """Load geometry metrics JSON from disk."""

    logger.info("load_geometry_metrics | start | output_path=%s", output_path)
    try:
        output_path = Path(output_path)
        if not output_path.exists():
            raise FileNotFoundError(f"Geometry metrics file not found: {output_path}")
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        logger.info(
            "load_geometry_metrics | done | output_path=%s | keys=%s",
            output_path,
            sorted(payload.keys()),
        )
        return payload
    except Exception:
        logger.exception("load_geometry_metrics | failed | output_path=%s", output_path)
        raise


def _measure_state(stl_path: Path) -> dict[str, Any]:
    """Measure one STL file with deterministic geometry metrics."""

    mesh = _load_mesh(stl_path)
    bounding_box_extents = [float(value) for value in np.asarray(mesh.bounding_box.extents, dtype=float)]
    center_of_mass = [float(value) for value in np.asarray(mesh.center_mass, dtype=float)]
    components = mesh.split(only_watertight=False)
    connected_component_count = len(components) if components else 0
    return {
        "stl_path": str(stl_path),
        "bounding_box_extents_mm": bounding_box_extents,
        "volume_mm3": float(mesh.volume),
        "surface_area_mm2": float(mesh.area),
        "center_of_mass_mm": center_of_mass,
        "connected_component_count": connected_component_count,
        "is_watertight": bool(mesh.is_watertight),
    }


def _measure_pairwise_deltas(states: Mapping[str, Mapping[str, Any]], ordered_labels: list[str]) -> dict[str, dict[str, Any]]:
    """Compute adjacent and end-to-end deltas for measured states."""

    deltas: dict[str, dict[str, Any]] = {}
    for left_label, right_label in zip(ordered_labels, ordered_labels[1:]):
        deltas[f"{right_label}_minus_{left_label}"] = _delta_state(states[left_label], states[right_label])
    if len(ordered_labels) >= 3:
        deltas[f"{ordered_labels[-1]}_minus_{ordered_labels[0]}"] = _delta_state(
            states[ordered_labels[0]],
            states[ordered_labels[-1]],
        )
    return deltas


def _delta_state(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """Compute a numeric delta between two state measurements."""

    return {
        "bounding_box_extents_mm": [
            float(right_value) - float(left_value)
            for left_value, right_value in zip(left["bounding_box_extents_mm"], right["bounding_box_extents_mm"])
        ],
        "volume_mm3": float(right["volume_mm3"]) - float(left["volume_mm3"]),
        "surface_area_mm2": float(right["surface_area_mm2"]) - float(left["surface_area_mm2"]),
        "center_of_mass_mm": [
            float(right_value) - float(left_value)
            for left_value, right_value in zip(left["center_of_mass_mm"], right["center_of_mass_mm"])
        ],
        "connected_component_count": int(right["connected_component_count"]) - int(left["connected_component_count"]),
        "is_watertight_change": bool(right["is_watertight"]) != bool(left["is_watertight"]),
    }


def _load_mesh(stl_path: Path) -> trimesh.Trimesh:
    """Load a normalized Trimesh from disk."""

    stl_path = Path(stl_path)
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


def _ensure_can_write(output_path: Path, *, force: bool) -> None:
    """Refuse to overwrite existing geometry metrics unless force is enabled."""

    if force:
        return
    if output_path.exists():
        raise FileExistsError(f"Existing geometry metrics found at {output_path}. Use force=True to overwrite.")


def _infer_sample_id(output_path: Path) -> str:
    """Infer the sample id from the comparison output tree."""

    try:
        sample_dir = Path(output_path).parent.parent
        name = sample_dir.name
        if name.startswith("sample_"):
            return name.removeprefix("sample_")
    except Exception:
        pass
    return "unknown"
