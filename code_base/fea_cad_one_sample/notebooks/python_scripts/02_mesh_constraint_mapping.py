"""CLI mirror for the mesh and constraint-mapping notebook."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Sequence

MODULE_ROOT = Path(__file__).resolve().parents[2]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from src import interfaces as api

logger = logging.getLogger(__name__)
DEFAULT_SAMPLE_ID = "00689964"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the script mirror."""

    parser = argparse.ArgumentParser(
        prog="02_mesh_constraint_mapping.py",
        description="Mirror for the geometry preparation and mesh/region-mapping notebook.",
    )
    parser.add_argument("--sample-id", default=DEFAULT_SAMPLE_ID, help="Sample ID to inspect.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing derived artifacts.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the mesh mirror and return an exit code."""

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        run(args)
        return 0
    except Exception as exc:
        logger.exception("script 02 failed")
        sys.stderr.write(f"Error: {exc}\n")
        return 1


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Prepare geometry, generate the mesh, and print mesh region details."""

    module_root = MODULE_ROOT
    sample_dir = module_root / "outputs" / f"sample_{args.sample_id}"
    state_b_dir = sample_dir / "02_fea_constrained_revision"
    source_step_path = state_b_dir / "fea_revision.step"

    print("[STAGE] baseline config")
    config = api.build_baseline_config(
        run_dir=state_b_dir,
        source_step_path=source_step_path,
        mesh_size_mm=5.0,
        load_magnitude_n=200.0,
    )
    print(f"  ✓ run_dir        : {config.run_dir}")
    print(f"  ✓ source STEP    : {config.geometry.source_step_path}")
    print(f"  ✓ mesh size      : {config.mesh_size_mm} mm")
    print(f"  ✓ load magnitude : {config.load.magnitude_n} N")

    print("\n[STAGE] geometry preparation")
    geometry = api.prepare_geometry_artifacts(config, force=args.force)
    print(f"  ✓ geometry step   : {geometry.step_path}")
    print(f"  ✓ geometry stl    : {geometry.stl_path}")
    print(f"  ✓ geometry summary: {geometry.summary_path}")
    print(f"  ✓ preview         : {geometry.preview_path}")
    print(f"  ✓ major axis      : {geometry.major_axis}")

    print("\n[STAGE] mesh generation")
    mesh = api.generate_calculix_mesh(config, geometry, force=args.force)
    region = mesh.region_selection
    print(f"  ✓ inp path        : {mesh.inp_path}")
    print(f"  ✓ mesh path       : {state_b_dir / f'{config.job_name}.msh'}")
    print(f"  ✓ mesh summary    : {mesh.summary_path}")
    print(f"  ✓ mesh preview    : {mesh.preview_path}")
    print(f"  ✓ node count      : {mesh.node_count}")
    print(f"  ✓ element count   : {mesh.element_count}")
    print(f"  ✓ fixed nodes     : {len(region.fixed_node_ids)}")
    print(f"  ✓ load nodes      : {len(region.load_node_ids)}")
    print(f"  ✓ fixed node ids  : {region.fixed_node_ids[:10]}")
    print(f"  ✓ load node ids   : {region.load_node_ids[:10]}")

    return {
        "sample_id": args.sample_id,
        "state_b_dir": str(state_b_dir),
        "geometry_summary_path": str(geometry.summary_path),
        "mesh_summary_path": str(mesh.summary_path),
        "inp_path": str(mesh.inp_path),
    }


if __name__ == "__main__":
    raise SystemExit(main())
