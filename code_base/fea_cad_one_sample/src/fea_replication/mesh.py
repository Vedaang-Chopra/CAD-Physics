"""Mesh generation and CalculiX input export using Gmsh."""

# pyright: reportMissingImports=false

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import gmsh

from .schemas import FEAReplicationConfig, GeometrySummary, MeshSummary, RegionSelectionSummary
from .utils import chunked, write_json, write_text

logger = logging.getLogger(__name__)

_GMSH_TETRA_TO_CCX = {
    4: "C3D4",
    11: "C3D10",
}


def generate_calculix_mesh(config: FEAReplicationConfig, geometry: GeometrySummary, *, force: bool = False) -> MeshSummary:
    """Generate a 3D mesh and write a CalculiX-compatible input deck."""

    logger.info(
        "generate_calculix_mesh | start | step_path=%s | mesh_size_mm=%s | force=%s",
        geometry.step_path,
        config.mesh_size_mm,
        force,
    )
    try:
        run_dir = Path(config.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        inp_path = run_dir / f"{config.job_name}.inp"
        mesh_path = run_dir / f"{config.job_name}.msh"
        preview_path = run_dir / "mesh_preview.png"
        summary_path = run_dir / "mesh_summary.json"

        if not force and (inp_path.exists() or mesh_path.exists() or preview_path.exists() or summary_path.exists()):
            raise FileExistsError(f"Existing mesh artifacts found in {run_dir}. Use force=True to overwrite.")

        mesh_data = _mesh_step_geometry(
            step_path=geometry.step_path,
            mesh_size_mm=config.mesh_size_mm,
            major_axis=geometry.major_axis,
            selection_margin_fraction=config.selection_margin_fraction,
            selection_margin_min_mm=config.selection_margin_min_mm,
            output_mesh_path=mesh_path,
        )

        inp_text = _build_calculix_inp(config=config, geometry=geometry, mesh_data=mesh_data)
        write_text(inp_path, inp_text, force=True)
        preview_written = render_mesh_preview(
            node_coords=mesh_data["node_coords"],
            region_selection=mesh_data["region_selection"],
            geometry=geometry,
            output_path=preview_path,
            force=True,
        )

        summary = MeshSummary(
            inp_path=inp_path,
            preview_path=preview_written,
            summary_path=summary_path,
            node_count=len(mesh_data["node_coords"]),
            element_count=len(mesh_data["elements"]),
            element_type_counts=mesh_data["element_type_counts"],
            region_selection=mesh_data["region_selection"],
            geometry_step_path=geometry.step_path,
            mesh_size_mm=config.mesh_size_mm,
        )
        write_json(summary_path, mesh_summary_to_dict(summary), force=True)
        logger.info(
            "generate_calculix_mesh | done | inp_path=%s | node_count=%d | element_count=%d",
            inp_path,
            summary.node_count,
            summary.element_count,
        )
        return summary
    except Exception:
        logger.exception(
            "generate_calculix_mesh | failed | step_path=%s | mesh_size_mm=%s | force=%s",
            geometry.step_path,
            config.mesh_size_mm,
            force,
        )
        raise


def render_mesh_preview(
    node_coords: dict[int, tuple[float, float, float]],
    region_selection: RegionSelectionSummary,
    geometry: GeometrySummary,
    output_path: Path,
    *,
    force: bool = False,
) -> Path:
    """Render selected fixed and load nodes on top of the mesh node cloud."""

    logger.info(
        "render_mesh_preview | start | output_path=%s | force=%s",
        output_path,
        force,
    )
    try:
        output_path = Path(output_path)
        if output_path.exists() and not force:
            return output_path

        points = np.asarray(list(node_coords.values()), dtype=float)
        fixed_points = np.asarray([node_coords[node_id] for node_id in region_selection.fixed_node_ids], dtype=float)
        load_points = np.asarray([node_coords[node_id] for node_id in region_selection.load_node_ids], dtype=float)
        _plot_mesh_nodes(points, fixed_points, load_points, geometry=geometry, region_selection=region_selection, output_path=output_path)
        logger.info("render_mesh_preview | done | output_path=%s", output_path)
        return output_path
    except Exception:
        logger.exception("render_mesh_preview | failed | output_path=%s | force=%s", output_path, force)
        raise


def mesh_summary_to_dict(summary: MeshSummary) -> dict[str, Any]:
    """Convert a mesh summary into a JSON-friendly dictionary."""

    return {
        "inp_path": str(summary.inp_path),
        "preview_path": str(summary.preview_path),
        "summary_path": str(summary.summary_path),
        "node_count": summary.node_count,
        "element_count": summary.element_count,
        "element_type_counts": dict(summary.element_type_counts),
        "region_selection": region_selection_to_dict(summary.region_selection),
        "geometry_step_path": str(summary.geometry_step_path),
        "mesh_size_mm": summary.mesh_size_mm,
    }


def region_selection_to_dict(selection: RegionSelectionSummary) -> dict[str, Any]:
    """Convert a region selection summary into a JSON-friendly dictionary."""

    return {
        "major_axis": selection.major_axis,
        "axis_index": selection.axis_index,
        "lower_threshold_mm": selection.lower_threshold_mm,
        "upper_threshold_mm": selection.upper_threshold_mm,
        "fixed_node_ids": list(selection.fixed_node_ids),
        "load_node_ids": list(selection.load_node_ids),
        "fixed_node_count": len(selection.fixed_node_ids),
        "load_node_count": len(selection.load_node_ids),
    }


def _mesh_step_geometry(
    *,
    step_path: Path,
    mesh_size_mm: float,
    major_axis: str,
    selection_margin_fraction: float,
    selection_margin_min_mm: float,
    output_mesh_path: Path,
) -> dict[str, Any]:
    """Use Gmsh to mesh a STEP file and collect node/element data."""

    node_coords: dict[int, tuple[float, float, float]] = {}
    elements: list[tuple[int, list[int]]] = []
    element_type_counts: dict[str, int] = {}
    region_selection: RegionSelectionSummary | None = None

    with _gmsh_session():
        gmsh.model.add(output_mesh_path.stem)
        gmsh.model.occ.importShapes(str(step_path))
        gmsh.model.occ.synchronize()
        _configure_mesh_options(mesh_size_mm)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(output_mesh_path))

        node_coords = _collect_node_coordinates()
        elements, element_type_counts = _collect_volume_elements()
        region_selection = _select_end_regions(
            node_coords=node_coords,
            major_axis=major_axis,
            mesh_size_mm=mesh_size_mm,
            selection_margin_fraction=selection_margin_fraction,
            selection_margin_min_mm=selection_margin_min_mm,
        )

    if region_selection is None:
        raise RuntimeError("Could not derive fixed/load node sets from the mesh.")

    return {
        "node_coords": node_coords,
        "elements": elements,
        "element_type_counts": element_type_counts,
        "region_selection": region_selection,
    }


def _configure_mesh_options(mesh_size_mm: float) -> None:
    """Configure deterministic mesh sizing and quality options."""

    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size_mm)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size_mm)
    gmsh.option.setNumber("Mesh.CharacteristicLengthFromCurvature", 0)
    gmsh.option.setNumber("Mesh.CharacteristicLengthExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.ElementOrder", 1)
    gmsh.option.setNumber("Mesh.Optimize", 1)


def _collect_node_coordinates() -> dict[int, tuple[float, float, float]]:
    """Return all mesh nodes keyed by tag."""

    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    reshaped = np.asarray(coords, dtype=float).reshape(-1, 3)
    return {int(tag): (float(x), float(y), float(z)) for tag, (x, y, z) in zip(node_tags.tolist(), reshaped, strict=True)}


def _collect_volume_elements() -> tuple[list[tuple[int, list[int]]], dict[str, int]]:
    """Return the meshed 3D elements and CalculiX type counts."""

    elements: list[tuple[int, list[int]]] = []
    type_counts: dict[str, int] = {}
    element_types, element_tags, element_node_tags = gmsh.model.mesh.getElements(3)
    for element_type, tags, nodes in zip(element_types, element_tags, element_node_tags, strict=True):
        ccx_type = _gmsh_element_type_to_ccx(int(element_type))
        num_nodes = int(gmsh.model.mesh.getElementProperties(int(element_type))[3])
        flat_nodes = [int(tag) for tag in nodes.tolist()]
        if len(flat_nodes) != len(tags) * num_nodes:
            raise ValueError(f"Unexpected node count for Gmsh element type {element_type}.")
        type_counts[ccx_type] = type_counts.get(ccx_type, 0) + len(tags)
        for index, element_tag in enumerate(tags.tolist()):
            start = index * num_nodes
            end = start + num_nodes
            elements.append((int(element_tag), flat_nodes[start:end]))
    elements.sort(key=lambda item: item[0])
    return elements, type_counts


@contextlib.contextmanager
def _gmsh_session():
    """Initialize and finalize Gmsh safely."""

    gmsh.initialize()
    try:
        yield
    finally:
        gmsh.finalize()


def _select_end_regions(
    *,
    node_coords: dict[int, tuple[float, float, float]],
    major_axis: str,
    mesh_size_mm: float,
    selection_margin_fraction: float,
    selection_margin_min_mm: float,
) -> RegionSelectionSummary:
    """Select node sets near the minimum and maximum faces along the major axis."""

    axis_index = {"X": 0, "Y": 1, "Z": 2}[major_axis]
    coords = np.asarray(list(node_coords.values()), dtype=float)
    axis_values = coords[:, axis_index]
    axis_min = float(axis_values.min())
    axis_max = float(axis_values.max())
    axis_span = max(axis_max - axis_min, 1.0e-9)
    band = max(mesh_size_mm * 1.5, axis_span * selection_margin_fraction, selection_margin_min_mm)
    lower_threshold = axis_min + band
    upper_threshold = axis_max - band

    fixed_node_ids = [node_id for node_id, xyz in node_coords.items() if xyz[axis_index] <= lower_threshold]
    load_node_ids = [node_id for node_id, xyz in node_coords.items() if xyz[axis_index] >= upper_threshold]

    if not fixed_node_ids:
        fixed_node_ids = [_nearest_node_id(node_coords, axis_index, axis_min)]
    if not load_node_ids:
        load_node_ids = [_nearest_node_id(node_coords, axis_index, axis_max)]

    fixed_node_ids = sorted(set(fixed_node_ids))
    load_node_ids = sorted(set(load_node_ids))
    return RegionSelectionSummary(
        major_axis=major_axis,
        axis_index=axis_index,
        lower_threshold_mm=lower_threshold,
        upper_threshold_mm=upper_threshold,
        fixed_node_ids=fixed_node_ids,
        load_node_ids=load_node_ids,
    )


def _nearest_node_id(node_coords: dict[int, tuple[float, float, float]], axis_index: int, target_value: float) -> int:
    """Return the node closest to one coordinate value on a given axis."""

    best_node_id = -1
    best_distance = float("inf")
    for node_id, xyz in node_coords.items():
        distance = abs(xyz[axis_index] - target_value)
        if distance < best_distance:
            best_distance = distance
            best_node_id = node_id
    if best_node_id < 0:
        raise ValueError("Could not identify a boundary node.")
    return best_node_id


def _gmsh_element_type_to_ccx(element_type: int) -> str:
    """Map Gmsh volume element types to CalculiX element types."""

    if element_type not in _GMSH_TETRA_TO_CCX:
        raise ValueError(f"Unsupported Gmsh element type: {element_type}. Expected first-order tetrahedra.")
    return _GMSH_TETRA_TO_CCX[element_type]


def _build_calculix_inp(config: FEAReplicationConfig, geometry: GeometrySummary, mesh_data: dict[str, Any]) -> str:
    """Render a complete CalculiX input deck for the mesh."""

    node_lines = _render_node_block(mesh_data["node_coords"])
    element_lines = _render_element_block(mesh_data["elements"])
    fixed_lines = _render_set_block("NSET", config.boundary_condition.fixed_node_set, mesh_data["region_selection"].fixed_node_ids)
    load_lines = _render_set_block("NSET", config.load.target_node_set, mesh_data["region_selection"].load_node_ids)
    all_node_lines = _render_set_block("NSET", "ALL_NODES", list(mesh_data["node_coords"].keys()))
    all_element_ids = [element_id for element_id, _ in mesh_data["elements"]]
    element_set_lines = _render_set_block("ELSET", "ALL_ELEMENTS", all_element_ids)
    load_vector = _normalize_vector(config.load.direction_vector)
    load_components = [config.load.magnitude_n * component for component in load_vector]
    load_lines_block = _render_cload_block(mesh_data["region_selection"].load_node_ids, load_components)
    material_name = config.material.name.upper().replace(" ", "_")
    youngs_modulus_mpa = config.material.youngs_modulus_pa / 1_000_000.0

    return "\n".join(
        [
            "*HEADING",
            f"FEA replication pipeline: {geometry.name}",
            f"** Geometry source: {geometry.step_path}",
            f"** Units: mm, N, MPa (material inputs converted from Pa)",
            "**",
            node_lines,
            element_lines,
            fixed_lines,
            load_lines,
            all_node_lines,
            element_set_lines,
            f"*MATERIAL, NAME={material_name}",
            "*ELASTIC",
            f"{youngs_modulus_mpa:.6f}, {config.material.poissons_ratio:.6f}",
            f"*SOLID SECTION, ELSET=ALL_ELEMENTS, MATERIAL={material_name}",
            "*STEP",
            "*STATIC",
            "1., 1., 1.0E-05, 1.",
            f"*BOUNDARY",
            f"{config.boundary_condition.fixed_node_set}, 1, 3",
            "*CLOAD",
            load_lines_block,
            "*NODE FILE",
            "U",
            "*EL FILE",
            "S",
            "*NODE PRINT, NSET=ALL_NODES",
            "U",
            "*EL PRINT, ELSET=ALL_ELEMENTS",
            "S",
            "*END STEP",
        ]
    )


def _render_node_block(node_coords: dict[int, tuple[float, float, float]]) -> str:
    """Render the *NODE block."""

    lines = ["*NODE"]
    for node_id in sorted(node_coords):
        x, y, z = node_coords[node_id]
        lines.append(f"{node_id}, {x:.6f}, {y:.6f}, {z:.6f}")
    return "\n".join(lines)


def _render_element_block(elements: list[tuple[int, list[int]]]) -> str:
    """Render the *ELEMENT block."""

    lines = ["*ELEMENT, TYPE=C3D4, ELSET=ALL_ELEMENTS"]
    for element_id, node_ids in elements:
        lines.append(f"{element_id}, {', '.join(str(node_id) for node_id in node_ids)}")
    return "\n".join(lines)


def _render_set_block(set_keyword: str, set_name: str, ids: list[int]) -> str:
    """Render a *NSET or *ELSET block."""

    lines = [f"*{set_keyword}, {set_keyword}={set_name}"]
    for chunk in chunked(sorted(ids), 16):
        lines.append(", ".join(str(item) for item in chunk))
    return "\n".join(lines)


def _render_cload_block(node_ids: list[int], load_components: list[float]) -> str:
    """Render a distributed *CLOAD block over the selected load nodes."""

    lines: list[str] = []
    node_count = max(len(node_ids), 1)
    for node_id in sorted(node_ids):
        for dof_index, component in enumerate(load_components, start=1):
            if abs(component) < 1.0e-12:
                continue
            lines.append(f"{node_id}, {dof_index}, {component / node_count:.6f}")
    return "\n".join(lines) if lines else "0, 1, 0.0"


def _normalize_vector(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    """Normalize a 3D vector, raising for the zero vector."""

    arr = np.asarray(vector, dtype=float)
    length = float(np.linalg.norm(arr))
    if length <= 0.0:
        raise ValueError("Load direction vector must be non-zero.")
    normalized = arr / length
    return float(normalized[0]), float(normalized[1]), float(normalized[2])


def _plot_mesh_nodes(
    points: np.ndarray,
    fixed_points: np.ndarray,
    load_points: np.ndarray,
    *,
    geometry: GeometrySummary,
    region_selection: RegionSelectionSummary,
    output_path: Path,
) -> None:
    """Render the mesh nodes and selected end regions."""

    fig = plt.figure(figsize=(6.0, 4.8), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    if len(points):
        ax.scatter(xs=points[:, 0], ys=points[:, 1], zs=points[:, 2], s=2, c="#c7c7c7", alpha=0.4, label="all nodes")  # type: ignore[arg-type]
    if len(fixed_points):
        ax.scatter(xs=fixed_points[:, 0], ys=fixed_points[:, 1], zs=fixed_points[:, 2], s=10, c="#b71c1c", label="fixed nodes")  # type: ignore[arg-type]
    if len(load_points):
        ax.scatter(xs=load_points[:, 0], ys=load_points[:, 1], zs=load_points[:, 2], s=10, c="#1565c0", label="load nodes")  # type: ignore[arg-type]
    mins = np.asarray(geometry.bbox_min_mm, dtype=float)
    maxs = np.asarray(geometry.bbox_max_mm, dtype=float)
    center = (mins + maxs) / 2.0
    max_span = float(np.max(np.maximum(maxs - mins, 1.0e-6)))
    half_span = max_span * 0.60
    ax.set_xlim(center[0] - half_span, center[0] + half_span)
    ax.set_ylim(center[1] - half_span, center[1] + half_span)
    ax.set_zlim(center[2] - half_span, center[2] + half_span)
    ax.view_init(elev=25.0, azim=-45.0)
    ax.set_box_aspect((1.0, 1.0, 1.0))
    ax.set_title(
        f"{geometry.name} mesh | axis={region_selection.major_axis} | fixed={len(region_selection.fixed_node_ids)} | load={len(region_selection.load_node_ids)}"
    )
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")
    ax.legend(loc="upper left", fontsize=7)
    fig.tight_layout(pad=0.2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
