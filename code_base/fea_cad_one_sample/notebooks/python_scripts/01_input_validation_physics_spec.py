"""CLI mirror for the input-validation and physics-spec notebook."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Sequence

MODULE_ROOT = Path(__file__).resolve().parents[2]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from src import interfaces as api

logger = logging.getLogger(__name__)
DEFAULT_CONFIG_NAME = "config_gpt_5_4_mini.yaml"
DEFAULT_SAMPLE_ID = "00689964"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the script mirror."""

    parser = argparse.ArgumentParser(
        prog="01_input_validation_physics_spec.py",
        description="Mirror for the State A/B artifact validation and physics-spec notebook.",
    )
    parser.add_argument("--sample-id", default=DEFAULT_SAMPLE_ID, help="Sample ID to inspect.")
    parser.add_argument(
        "--config-name",
        default=DEFAULT_CONFIG_NAME,
        help="Config filename stored in the baseline config object.",
    )
    parser.add_argument("--force", action="store_true", help="Allow overwriting derived artifacts if any are written.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the validation mirror and return an exit code."""

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        run(args)
        return 0
    except Exception as exc:
        logger.exception("script 01 failed")
        sys.stderr.write(f"Error: {exc}\n")
        return 1


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Validate the State A and State B artifacts and display the physics defaults."""

    module_root = MODULE_ROOT
    sample_dir = module_root / "outputs" / f"sample_{args.sample_id}"
    state_a_dir = sample_dir / "01_dataset_original"
    state_b_dir = sample_dir / "02_fea_constrained_revision"
    state_b_step = state_b_dir / "fea_revision.step"

    print("[STAGE] required artifact check")
    required_paths = [
        state_a_dir / "original_prompt.txt",
        state_a_dir / "database_original_code.py",
        state_a_dir / "original.step",
        state_a_dir / "original.stl",
        state_b_dir / "load_case.json",
        state_b_dir / "selector_hints.json",
        state_b_step,
        state_b_dir / "fea_revision.stl",
    ]
    _require_paths(required_paths)
    for path in required_paths:
        print(f"  ✓ {path}")

    print("\n[STAGE] load-case and selector-hint inspection")
    load_case = api.LoadCase(**json.loads((state_b_dir / "load_case.json").read_text(encoding="utf-8")))
    selector_hints = api.SelectorHints(**json.loads((state_b_dir / "selector_hints.json").read_text(encoding="utf-8")))
    print(f"  ✓ load_case.sample_id : {load_case.sample_id}")
    print(f"  ✓ load_case.material  : {load_case.material.get('name')} / E={load_case.material.get('youngs_modulus_pa')} Pa")
    print(f"  ✓ load_case.load      : {load_case.loads[0].get('magnitude_n')} N")
    print(f"  ✓ selector fixed     : {selector_hints.fixed_region_description}")
    print(f"  ✓ selector load      : {selector_hints.load_region_description}")

    print("\n[STAGE] baseline physics specification")
    config = api.build_baseline_config(
        run_dir=state_b_dir,
        source_step_path=state_b_step,
        mesh_size_mm=5.0,
        load_magnitude_n=200.0,
    )
    print(f"  ✓ run_dir           : {config.run_dir}")
    print(f"  ✓ source STEP       : {config.geometry.source_step_path}")
    print(f"  ✓ mesh size         : {config.mesh_size_mm} mm")
    print(f"  ✓ load magnitude    : {config.load.magnitude_n} N")
    print(f"  ✓ load direction    : {config.load.direction_vector}")
    print(f"  ✓ fixed node set    : {config.boundary_condition.fixed_node_set}")
    print(f"  ✓ load node set     : {config.load.target_node_set}")
    print(f"  ✓ displacement cap  : {config.verification_criteria.max_displacement_mm} mm")
    print(f"  ✓ safety factor min : {config.verification_criteria.required_safety_factor}")

    return {
        "sample_id": args.sample_id,
        "state_a_dir": str(state_a_dir),
        "state_b_dir": str(state_b_dir),
        "source_step_path": str(state_b_step),
    }


def _require_paths(paths: list[Path]) -> None:
    """Raise a clear error if any required artifact is missing."""

    missing = [str(path) for path in paths if not Path(path).exists()]
    if missing:
        raise FileNotFoundError("Missing required artifacts: " + ", ".join(missing))


if __name__ == "__main__":
    raise SystemExit(main())
