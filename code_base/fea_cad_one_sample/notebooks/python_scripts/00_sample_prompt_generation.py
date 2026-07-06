"""CLI mirror for the sample and prompt-generation notebook."""

from __future__ import annotations

import argparse
import logging
import os
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
DEFAULT_SELECTION_SOURCE = "dataset"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the script mirror."""

    parser = argparse.ArgumentParser(
        prog="00_sample_prompt_generation.py",
        description="Mirror for the sample loading, State A persistence, and State B prompt generation notebook.",
    )
    parser.add_argument("--sample-id", default=DEFAULT_SAMPLE_ID, help="Sample ID to inspect.")
    parser.add_argument(
        "--selection-source",
        choices=("dataset", "db"),
        default=DEFAULT_SELECTION_SOURCE,
        help="Load the sample from the local dataset artifacts or the live DB.",
    )
    parser.add_argument(
        "--connection-string",
        default=None,
        help="Optional CAD DB connection string when --selection-source=db.",
    )
    parser.add_argument(
        "--config-name",
        default=DEFAULT_CONFIG_NAME,
        help="Config filename stored in the pipeline config object.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing artifacts.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the notebook mirror and return an exit code."""

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        run(args)
        return 0
    except Exception as exc:
        logger.exception("script 00 failed")
        sys.stderr.write(f"Error: {exc}\n")
        return 1


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute the sample-loading and prompt-generation workflow."""

    module_root = MODULE_ROOT
    sample_dir = module_root / "outputs" / f"sample_{args.sample_id}"
    state_a_dir = sample_dir / "01_dataset_original"
    state_b_dir = sample_dir / "02_fea_constrained_revision"
    state_a_views_dir = state_a_dir / "views"
    state_b_views_dir = state_b_dir / "views"

    print("[STAGE] sample load")
    connection_string = _resolve_connection_string(args.connection_string)
    sample = api.load_selected_sample(
        module_root=module_root,
        sample_id=args.sample_id,
        selection_source=args.selection_source,
        connection_string=connection_string,
    )
    print(f"  ✓ sample_id: {sample.sample_id}")
    print(f"  ✓ source   : {sample.source}")
    print(f"  ✓ prompt   : {len(sample.prompt.splitlines())} lines")
    print(f"  ✓ code     : {len((sample.ground_truth_code or '').splitlines())} lines")

    print("\n[STAGE] state A persistence")
    config = _build_pipeline_config(module_root, args.config_name, force=args.force)
    original_code = api.generate_original_code(sample, config)
    original_exec = api.execute_and_export_cadquery(original_code, state_a_dir, basename="original", force=args.force)
    original_views = api.render_views(Path(original_exec["stl_path"]), state_a_views_dir, force=args.force)
    print(f"  ✓ prompt path: {state_a_dir / 'original_prompt.txt'}")
    print(f"  ✓ code path  : {state_a_dir / 'database_original_code.py'}")
    print(f"  ✓ step path  : {original_exec['step_path']}")
    print(f"  ✓ stl path   : {original_exec['stl_path']}")
    print(f"  ✓ views      : {sorted(original_views.values())}")

    print("\n[STAGE] State B prompt and revision")
    load_case = api.write_load_case(sample.sample_id, state_b_dir / "load_case.json", force=args.force)
    selector_hints = api.write_selector_hints(load_case, state_b_dir / "selector_hints.json", force=args.force)
    revision = api.revise_code_for_fea(sample.prompt, original_code, load_case, selector_hints, config)
    revision_code = revision.code_path.read_text(encoding="utf-8")
    revision_exec = api.execute_and_export_fea_revision_cadquery(revision_code, state_b_dir, force=args.force)
    revision_views = api.render_views(Path(revision_exec["stl_path"]), state_b_views_dir, force=args.force)
    annotated_path = api.render_support_load_annotation(
        Path(revision_exec["stl_path"]),
        state_b_views_dir / "annotated_support_load.png",
        selector_hints,
        force=args.force,
    )
    print(f"  ✓ load case  : {state_b_dir / 'load_case.json'}")
    print(f"  ✓ hints      : {state_b_dir / 'selector_hints.json'}")
    print(f"  ✓ prompt     : {revision.prompt_path}")
    print(f"  ✓ code       : {revision.code_path}")
    print(f"  ✓ change log  : {revision.change_log_path}")
    print(f"  ✓ step path   : {revision_exec['step_path']}")
    print(f"  ✓ stl path    : {revision_exec['stl_path']}")
    print(f"  ✓ views       : {sorted(revision_views.values())}")
    print(f"  ✓ annotation  : {annotated_path}")

    return {
        "sample_id": sample.sample_id,
        "state_a_dir": str(state_a_dir),
        "state_b_dir": str(state_b_dir),
        "original_step_path": original_exec["step_path"],
        "revision_step_path": revision_exec["step_path"],
        "revision_prompt_path": str(revision.prompt_path),
    }


def _build_pipeline_config(module_root: Path, config_name: str, *, force: bool) -> api.PipelineConfig:
    """Build the public pipeline config object used by the notebook mirror."""

    return api.PipelineConfig(
        config_name=config_name,
        config_path=module_root / "src" / "copied_from_cadcodeverify" / "configs" / config_name,
        output_root=module_root / "outputs",
        force=force,
    )


def _resolve_connection_string(explicit_connection_string: str | None) -> str | None:
    """Resolve the optional CAD DB connection string from the environment."""

    return explicit_connection_string or os.environ.get("CAD_DB_CONNECTION_STRING")


if __name__ == "__main__":
    raise SystemExit(main())
