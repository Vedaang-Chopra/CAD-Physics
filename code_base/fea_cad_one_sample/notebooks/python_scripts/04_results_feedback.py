"""CLI mirror for the results and feedback notebook."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

MODULE_ROOT = Path(__file__).resolve().parents[2]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from src import interfaces as api

logger = logging.getLogger(__name__)
DEFAULT_SAMPLE_ID = "00689964"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the script mirror."""

    parser = argparse.ArgumentParser(
        prog="04_results_feedback.py",
        description="Mirror for the results parsing, manual-gate inspection, and feedback notebook.",
    )
    parser.add_argument("--sample-id", default=DEFAULT_SAMPLE_ID, help="Sample ID to inspect.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing derived artifacts.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the results mirror and return an exit code."""

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        run(args)
        return 0
    except Exception as exc:
        logger.exception("script 04 failed")
        sys.stderr.write(f"Error: {exc}\n")
        return 1


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Inspect solver results, the manual gate, and build comparison artifacts."""

    module_root = MODULE_ROOT
    sample_dir = module_root / "outputs" / f"sample_{args.sample_id}"
    state_a_dir = sample_dir / "01_dataset_original"
    state_b_dir = sample_dir / "02_fea_constrained_revision"
    manual_dir = sample_dir / "04_manual_freecad_fea"
    comparison_dir = sample_dir / "03_comparison"
    state_c_dir = sample_dir / "05_post_fea_revision"

    original_prompt_path = state_a_dir / "original_prompt.txt"
    original_code_path = state_a_dir / "database_original_code.py"
    revision_prompt_path = state_b_dir / "fea_revision_prompt.txt"
    revision_code_path = state_b_dir / "fea_revision_code.py"
    load_case_path = state_b_dir / "load_case.json"
    revision_change_log_path = state_b_dir / "fea_revision_change_log.json"
    manual_report_path = manual_dir / "fea_report.json"
    screenshots_dir = manual_dir / "screenshots"

    print("[STAGE] solver results")
    solver_summary = _load_solver_summary_if_present(state_b_dir)
    parsed_results = None
    if solver_summary is not None:
        config = api.build_baseline_config(
            run_dir=state_b_dir,
            source_step_path=state_b_dir / "fea_revision.step",
            mesh_size_mm=5.0,
            load_magnitude_n=200.0,
        )
        parsed_results = api.parse_calculix_results(config, solver_summary)
        print(f"  ✓ dat path      : {parsed_results.dat_path}")
        print(f"  ✓ max disp      : {parsed_results.max_displacement_mm}")
        print(f"  ✓ max stress    : {parsed_results.max_von_mises_mpa}")
        print(f"  ✓ overall pass  : {parsed_results.overall_pass}")
    else:
        print(f"  ✗ no solver results found under {state_b_dir}")

    print("\n[STAGE] manual FEA gate")
    load_case = api.LoadCase(**_load_json(load_case_path))
    manual_report = _load_json(manual_report_path) if manual_report_path.exists() else {}
    evidence_paths = sorted(path for path in screenshots_dir.glob("*.png")) if screenshots_dir.exists() else []
    validation = api.validate_manual_fea_completion(manual_report, evidence_paths)
    print(f"  ✓ manual report  : {manual_report_path if manual_report_path.exists() else '<missing>'}")
    print(f"  ✓ evidence count : {len(evidence_paths)}")
    print(f"  ✓ is complete    : {validation['is_complete']}")
    if validation["missing_fields"]:
        print(f"  ✓ missing fields : {validation['missing_fields']}")
    if validation["missing_evidence_paths"]:
        print(f"  ✓ missing paths  : {validation['missing_evidence_paths']}")

    print("\n[STAGE] A/B comparison artifacts")
    original_prompt = _load_text(original_prompt_path)
    original_code = _load_text(original_code_path)
    revision_prompt = _load_text(revision_prompt_path)
    revision_code = _load_text(revision_code_path)
    revision_change_log = _load_json(revision_change_log_path)

    geometry_metrics = api.compute_geometry_metrics(
        {
            "state_a": state_a_dir / "original.stl",
            "state_b": state_b_dir / "fea_revision.stl",
        },
        comparison_dir / "geometry_metrics.json",
        force=args.force,
    )
    geometry_metrics_md = api.build_geometry_metrics_markdown(
        geometry_metrics,
        comparison_dir / "geometry_metrics.md",
        force=args.force,
    )
    prompt_diffs_path = api.build_prompt_and_code_diffs_report(
        original_prompt,
        revision_prompt,
        original_code,
        revision_code,
        comparison_dir / "prompt_and_code_diffs.md",
        force=args.force,
    )
    change_log_summary_path = api.build_change_log_summary(
        revision_change_log,
        comparison_dir / "change_log_summary.md",
        force=args.force,
    )
    print(f"  ✓ geometry json : {comparison_dir / 'geometry_metrics.json'}")
    print(f"  ✓ geometry md   : {geometry_metrics_md}")
    print(f"  ✓ prompt diffs  : {prompt_diffs_path}")
    print(f"  ✓ change log    : {change_log_summary_path}")

    result: dict[str, Any] = {
        "sample_id": args.sample_id,
        "parsed_results_path": str(parsed_results.summary_path) if parsed_results is not None else None,
        "manual_gate_complete": validation["is_complete"],
        "geometry_metrics_path": str(comparison_dir / "geometry_metrics.json"),
        "comparison_dir": str(comparison_dir),
    }

    print("\n[STAGE] State C promotion (when manual evidence is complete)")
    if validation["is_complete"]:
        pipeline_config = _build_pipeline_config(args.force)
        post_revision = api.revise_code_after_fea(
            revision_code,
            load_case,
            manual_report,
            evidence_paths,
            pipeline_config,
        )
        post_revision_code = post_revision.code_path.read_text(encoding="utf-8")
        post_exec = api.execute_and_export_post_fea_revision_cadquery(post_revision_code, state_c_dir, force=args.force)
        post_views = api.render_views(Path(post_exec["stl_path"]), state_c_dir / "views", force=args.force)
        state_abc_grid_path = api.build_state_abc_grid(
            state_a_dir / "views",
            state_b_dir / "views",
            state_c_dir / "views",
            comparison_dir / "state_abc_grid.png",
            force=args.force,
        )
        final_report_path = api.build_final_experiment_report(
            args.sample_id,
            comparison_dir,
            geometry_metrics,
            prompt_diffs_path,
            change_log_summary_path,
            state_abc_grid_path,
            report_summary={
                "solver_status": parsed_results.overall_pass if parsed_results is not None else None,
                "manual_gate_complete": validation["is_complete"],
                "post_fea_prompt_path": str(post_revision.prompt_path),
            },
            force=args.force,
        )
        result.update(
            {
                "post_fea_prompt_path": str(post_revision.prompt_path),
                "post_fea_code_path": str(post_revision.code_path),
                "post_fea_step_path": str(post_exec["step_path"]),
                "post_fea_stl_path": str(post_exec["stl_path"]),
                "state_abc_grid_path": str(state_abc_grid_path),
                "final_report_path": str(final_report_path),
            }
        )
        print(f"  ✓ post prompt  : {post_revision.prompt_path}")
        print(f"  ✓ post code    : {post_revision.code_path}")
        print(f"  ✓ post step    : {post_exec['step_path']}")
        print(f"  ✓ post stl     : {post_exec['stl_path']}")
        print(f"  ✓ abc grid     : {state_abc_grid_path}")
        print(f"  ✓ final report : {final_report_path}")
        print(f"  ✓ post views   : {sorted(post_views.values())}")
    else:
        print("  ✗ manual evidence incomplete; skipping State C promotion.")

    return result


def _load_solver_summary_if_present(state_b_dir: Path) -> api.SolverRunSummary | None:
    """Load the public solver summary dataclass if a CalculiX run completed."""

    dat_path = state_b_dir / "analysis.dat"
    if not dat_path.exists():
        return None
    stdout_path = state_b_dir / "analysis.stdout.txt"
    stderr_path = state_b_dir / "analysis.stderr.txt"
    frd_path = state_b_dir / "analysis.frd"
    sta_path = state_b_dir / "analysis.sta"
    cvg_path = state_b_dir / "analysis.cvg"
    return api.SolverRunSummary(
        job_name="analysis",
        run_dir=state_b_dir,
        input_path=state_b_dir / "analysis.inp",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        dat_path=dat_path,
        frd_path=frd_path,
        sta_path=sta_path,
        cvg_path=cvg_path if cvg_path.exists() else None,
        return_code=0,
        ccx_executable=shutil.which("ccx") or "ccx",
        output_files=sorted(path for path in state_b_dir.glob("analysis.*") if path.is_file()),
    )


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON artifact from disk."""

    if not path.exists():
        raise FileNotFoundError(f"Missing required JSON artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_text(path: Path) -> str:
    """Load a text artifact from disk."""

    if not path.exists():
        raise FileNotFoundError(f"Missing required text artifact: {path}")
    return path.read_text(encoding="utf-8")


def _build_pipeline_config(force: bool) -> api.PipelineConfig:
    """Build the public pipeline config required by the State C helper."""

    return api.PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=MODULE_ROOT / "src" / "copied_from_cadcodeverify" / "configs" / "config_gpt_5_4_mini.yaml",
        output_root=MODULE_ROOT / "outputs",
        force=force,
    )


if __name__ == "__main__":
    raise SystemExit(main())
