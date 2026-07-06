from __future__ import annotations

from pathlib import Path

import src.interfaces as iface


def test_build_baseline_config_defaults(tmp_path: Path) -> None:
    """Baseline config should expose the requested FEA fields."""

    config = iface.build_baseline_config(run_dir=tmp_path)

    assert config.material.name == "Aluminum 6061"
    assert config.material.youngs_modulus_pa == 69_000_000_000.0
    assert config.load.magnitude_n == 100.0
    assert config.boundary_condition.fixed_node_set == "FIXED_END"
    assert config.verification_criteria.max_displacement_mm == 2.0


def test_placeholder_geometry_and_mesh_smoke(tmp_path: Path) -> None:
    """The geometry and mesh stages should work without CalculiX."""

    config = iface.build_baseline_config(run_dir=tmp_path, mesh_size_mm=8.0, load_magnitude_n=100.0)
    geometry = iface.prepare_geometry_artifacts(config, force=True)
    mesh = iface.generate_calculix_mesh(config, geometry, force=True)

    assert geometry.step_path.exists()
    assert geometry.preview_path.exists()
    assert geometry.summary_path.exists()
    assert mesh.inp_path.exists()
    assert mesh.preview_path.exists()
    assert mesh.summary_path.exists()
    assert mesh.node_count > 0
    assert mesh.element_count > 0
    assert mesh.region_selection.major_axis == "X"
    assert len(mesh.region_selection.fixed_node_ids) > 0
    assert len(mesh.region_selection.load_node_ids) > 0
