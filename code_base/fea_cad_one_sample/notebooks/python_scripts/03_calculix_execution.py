"""CLI mirror for the CalculiX execution notebook."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
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
        prog="03_calculix_execution.py",
        description="Mirror for the solver preflight and CalculiX execution notebook.",
    )
    parser.add_argument("--sample-id", default=DEFAULT_SAMPLE_ID, help="Sample ID to inspect.")
    parser.add_argument("--force", action="store_true", help="Overwrite solver outputs if they exist.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the solver mirror and return an exit code."""

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        return run(args)
    except Exception as exc:
        logger.exception("script 03 failed")
        sys.stderr.write(f"Error: {exc}\n")
        return 1


def run(args: argparse.Namespace) -> int:
    """Preflight ccx, run the solver when available, and summarize results."""

    module_root = MODULE_ROOT
    sample_dir = module_root / "outputs" / f"sample_{args.sample_id}"
    state_b_dir = sample_dir / "02_fea_constrained_revision"
    mesh_summary_path = state_b_dir / "mesh_summary.json"
    inp_path = state_b_dir / f"analysis.inp"
    dat_path = state_b_dir / f"analysis.dat"

    print("[STAGE] baseline config and mesh summary")
    _require_paths([mesh_summary_path, inp_path])
    config = api.build_baseline_config(
        run_dir=state_b_dir,
        source_step_path=state_b_dir / "fea_revision.step",
        mesh_size_mm=5.0,
        load_magnitude_n=200.0,
    )
    mesh_summary = _load_mesh_summary(mesh_summary_path)
    print(f"  ✓ run_dir      : {config.run_dir}")
    print(f"  ✓ inp path     : {mesh_summary.inp_path}")
    print(f"  ✓ node count   : {mesh_summary.node_count}")
    print(f"  ✓ element count: {mesh_summary.element_count}")
    print(f"  ✓ fixed nodes  : {len(mesh_summary.region_selection.fixed_node_ids)}")
    print(f"  ✓ load nodes   : {len(mesh_summary.region_selection.load_node_ids)}")

    print("\n[STAGE] solver preflight")
    ccx_path = shutil.which(config.solver_executable)
    print(f"  ✓ {config.solver_executable} = {ccx_path}")
    if not ccx_path:
        message = (
            f"CalculiX executable '{config.solver_executable}' was not found on PATH. "
            "Install ccx before running the solver mirror."
        )
        print(f"  ✗ {message}")
        return 2

    print("\n[STAGE] solver execution")
    solver = api.run_calculix_solver(config, mesh_summary)
    print(f"  ✓ stdout  : {solver.stdout_path}")
    print(f"  ✓ stderr  : {solver.stderr_path}")
    print(f"  ✓ dat     : {solver.dat_path}")
    print(f"  ✓ frd     : {solver.frd_path}")
    print(f"  ✓ sta     : {solver.sta_path}")
    print(f"  ✓ cvg     : {solver.cvg_path}")
    print(f"  ✓ outputs : {[path.name for path in solver.output_files]}")

    if dat_path.exists():
        print(f"  ✓ dat size : {dat_path.stat().st_size} bytes")
    else:
        print(f"  ✗ missing dat file after solver run: {dat_path}")

    return 0


def _load_mesh_summary(path: Path) -> api.MeshSummary:
    """Load the public mesh summary dataclass from JSON."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    region_payload = payload["region_selection"]
    region = api.RegionSelectionSummary(
        major_axis=region_payload["major_axis"],
        axis_index=int(region_payload["axis_index"]),
        lower_threshold_mm=float(region_payload["lower_threshold_mm"]),
        upper_threshold_mm=float(region_payload["upper_threshold_mm"]),
        fixed_node_ids=[int(node_id) for node_id in region_payload.get("fixed_node_ids", [])],
        load_node_ids=[int(node_id) for node_id in region_payload.get("load_node_ids", [])],
    )
    return api.MeshSummary(
        inp_path=Path(payload["inp_path"]),
        preview_path=Path(payload["preview_path"]),
        summary_path=Path(payload["summary_path"]),
        node_count=int(payload["node_count"]),
        element_count=int(payload["element_count"]),
        element_type_counts={str(key): int(value) for key, value in payload.get("element_type_counts", {}).items()},
        region_selection=region,
        geometry_step_path=Path(payload["geometry_step_path"]),
        mesh_size_mm=float(payload["mesh_size_mm"]),
    )


def _require_paths(paths: list[Path]) -> None:
    """Raise a clear error if any required artifact is missing."""

    missing = [str(path) for path in paths if not Path(path).exists()]
    if missing:
        raise FileNotFoundError("Missing required artifacts: " + ", ".join(missing))


if __name__ == "__main__":
    raise SystemExit(main())
