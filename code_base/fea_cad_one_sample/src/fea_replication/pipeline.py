"""High-level orchestration for the deterministic FEA replication workflow."""

# pyright: reportMissingImports=false

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

from .geometry import geometry_summary_to_dict, prepare_geometry_artifacts
from .mesh import generate_calculix_mesh, mesh_summary_to_dict
from .results import parse_calculix_results, parsed_result_summary_to_dict
from .schemas import FEAReplicationConfig, GeometrySpec, LoadSpec
from .solver import run_calculix_solver, solver_summary_to_dict
from .utils import to_jsonable, write_json

logger = logging.getLogger(__name__)


def build_baseline_config(
    *,
    run_dir: Path,
    source_step_path: Path | None = None,
    mesh_size_mm: float = 5.0,
    load_magnitude_n: float = 100.0,
) -> FEAReplicationConfig:
    """Build the default Aluminum 6061 cantilever configuration."""

    logger.info(
        "build_baseline_config | start | run_dir=%s | source_step_path=%s | mesh_size_mm=%s | load_magnitude_n=%s",
        run_dir,
        source_step_path,
        mesh_size_mm,
        load_magnitude_n,
    )
    try:
        config = FEAReplicationConfig(
            run_dir=Path(run_dir),
            mesh_size_mm=float(mesh_size_mm),
            geometry=replace(
                GeometrySpec(),
                source_step_path=Path(source_step_path) if source_step_path is not None else None,
            ),
            load=LoadSpec(
                magnitude_n=float(load_magnitude_n),
                direction_vector=(0.0, 0.0, -1.0),
                target_region="free end face near maximum axis",
                target_node_set="LOAD_END",
            ),
        )
        logger.info("build_baseline_config | done | run_dir=%s", config.run_dir)
        return config
    except Exception:
        logger.exception(
            "build_baseline_config | failed | run_dir=%s | source_step_path=%s",
            run_dir,
            source_step_path,
        )
        raise


def run_full_replication(config: FEAReplicationConfig, *, force: bool = False) -> dict[str, Any]:
    """Run the full geometry → mesh → solver → result parsing pipeline."""

    logger.info("run_full_replication | start | run_dir=%s | force=%s", config.run_dir, force)
    try:
        geometry = prepare_geometry_artifacts(config, force=force)
        mesh = generate_calculix_mesh(config, geometry, force=force)
        solver = run_calculix_solver(config, mesh)
        results = parse_calculix_results(config, solver)
        payload = {
            "config": to_jsonable(config),
            "geometry": geometry_summary_to_dict(geometry),
            "mesh": mesh_summary_to_dict(mesh),
            "solver": solver_summary_to_dict(solver),
            "results": parsed_result_summary_to_dict(results),
        }
        summary_path = Path(config.run_dir) / "pipeline_summary.json"
        write_json(summary_path, payload, force=True)
        payload["summary_path"] = str(summary_path)
        logger.info(
            "run_full_replication | done | run_dir=%s | summary_path=%s",
            config.run_dir,
            summary_path,
        )
        return payload
    except Exception:
        logger.exception("run_full_replication | failed | run_dir=%s", config.run_dir)
        raise


def run_parametric_load_study(
    config: FEAReplicationConfig,
    load_values_n: list[float],
    *,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Run the full pipeline for a list of load magnitudes."""

    logger.info(
        "run_parametric_load_study | start | run_dir=%s | load_values_n=%s | force=%s",
        config.run_dir,
        load_values_n,
        force,
    )
    try:
        results: list[dict[str, Any]] = []
        for load_value in load_values_n:
            case_dir = Path(config.run_dir) / "parametric_study" / _load_slug(load_value)
            case_config = replace(
                config,
                run_dir=case_dir,
                load=replace(config.load, magnitude_n=float(load_value)),
            )
            run_result = run_full_replication(case_config, force=force)
            results.append(
                {
                    "load_magnitude_n": float(load_value),
                    "run_dir": str(case_config.run_dir),
                    "max_displacement_mm": run_result["results"]["max_displacement_mm"],
                    "max_von_mises_mpa": run_result["results"]["max_von_mises_mpa"],
                    "estimated_safety_factor": run_result["results"]["estimated_safety_factor"],
                    "passes_displacement": run_result["results"]["passes_displacement"],
                    "passes_safety_factor": run_result["results"]["passes_safety_factor"],
                    "overall_pass": run_result["results"]["overall_pass"],
                }
            )
        summary_path = Path(config.run_dir) / "parametric_study" / "parametric_study_results.json"
        write_json(summary_path, results, force=True)
        logger.info(
            "run_parametric_load_study | done | run_dir=%s | case_count=%d",
            config.run_dir,
            len(results),
        )
        return results
    except Exception:
        logger.exception("run_parametric_load_study | failed | run_dir=%s", config.run_dir)
        raise


def _load_slug(load_value_n: float) -> str:
    """Return a stable folder name for a load magnitude."""

    if float(load_value_n).is_integer():
        return f"load_{int(load_value_n):03d}N"
    return f"load_{str(load_value_n).replace('.', 'p')}N"
