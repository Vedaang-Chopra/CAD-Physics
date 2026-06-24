"""CLI entry point for the one-sample FEA prototype."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import runners

logger = logging.getLogger(__name__)
DEFAULT_CONFIG_NAME = "config_gpt_5_4_mini.yaml"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the one-sample prototype."""

    parser = argparse.ArgumentParser(
        prog="src.main",
        description="One-sample CAD-to-FEA prototype CLI.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        dest="global_force",
        help="Overwrite existing outputs when a command writes artifacts.",
    )

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=DEFAULT_CONFIG_NAME, help="Config filename to load.")
    common.add_argument("--sample-id", help="Explicit sample ID to load.")
    common.add_argument("--random", action="store_true", help="Select a random sample.")
    common.add_argument("--expert-random", action="store_true", help="Select a random FEA-sensible expert sample.")
    common.add_argument(
        "--force",
        action="store_true",
        dest="command_force",
        help="Overwrite existing outputs when a command writes artifacts.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inspect-schema", parents=[common], help="Inspect the configured database schema.")
    subparsers.add_parser("run", parents=[common], help="Run the full one-sample pipeline.")
    subparsers.add_parser("render-only", parents=[common], help="Render original and FEA-ready views only.")
    subparsers.add_parser("build-fea-prompt", parents=[common], help="Build the FEA-ready prompt only.")
    subparsers.add_parser(
        "build-freecad-instructions",
        parents=[common],
        help="Build the manual FreeCAD FEM instructions only.",
    )
    subparsers.add_parser("compare", parents=[common], help="Build the comparison artifacts only.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return an exit code."""

    logger.info("main | start | argv=%s", argv)
    parser = build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return int(exc.code or 0)

    force = bool(getattr(args, "global_force", False) or getattr(args, "command_force", False))
    try:
        exit_code = _dispatch(args, force=force)
        logger.info("main | done | command=%s | exit_code=%d", args.command, exit_code)
        return exit_code
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception as exc:
        logger.error("main | failed | error=%s", exc)
        sys.stderr.write(f"Error: {exc}\n")
        return 1


def _dispatch(args: argparse.Namespace, *, force: bool) -> int:
    """Dispatch one parsed CLI command."""

    if args.command == "inspect-schema":
        _validate_no_selection_flags(args, command="inspect-schema")
        return _run_inspect_schema(str(args.config), force=force)

    if args.command == "run":
        _validate_exactly_one_selection(args, command="run")
        summary = runners.run_full_pipeline_runner(
            str(args.config),
            getattr(args, "sample_id", None),
            bool(getattr(args, "random", False)),
            bool(getattr(args, "expert_random", False)),
            force,
        )
        _print_pipeline_summary(summary)
        return 0

    if args.command == "render-only":
        sample_id = _require_sample_id(args, "render-only")
        result = runners.render_only_runner(str(args.config), sample_id, force)
        _print_mapping(result)
        return 0

    if args.command == "build-fea-prompt":
        sample_id = _require_sample_id(args, "build-fea-prompt")
        result = runners.build_fea_prompt_only_runner(str(args.config), sample_id, force)
        _print_mapping(result)
        return 0

    if args.command == "build-freecad-instructions":
        sample_id = _require_sample_id(args, "build-freecad-instructions")
        result = runners.build_freecad_instructions_only_runner(str(args.config), sample_id, force)
        _print_mapping(result)
        return 0

    if args.command == "compare":
        sample_id = _require_sample_id(args, "compare")
        result = runners.compare_only_runner(str(args.config), sample_id, force)
        _print_mapping(result)
        return 0

    raise RuntimeError(f"Unsupported command: {args.command}")


def _run_inspect_schema(config_name: str, force: bool = False) -> int:
    """Load the configured DB connection string and print its schema summary."""

    logger.info("inspect-schema | start | config_name=%s | force=%s", config_name, force)
    summary = runners.inspect_schema_runner(config_name)
    sys.stdout.write(_format_schema_summary(summary))
    logger.info(
        "inspect-schema | done | config_name=%s | table_count=%s | force=%s",
        config_name,
        summary.get("table_count"),
        force,
    )
    return 0


def _validate_no_selection_flags(args: argparse.Namespace, command: str) -> None:
    """Reject sample-selection flags for commands that do not accept them."""

    if any([getattr(args, "sample_id", None), getattr(args, "random", False), getattr(args, "expert_random", False)]):
        raise ValueError(f"{command} does not accept sample-selection flags.")



def _validate_exactly_one_selection(args: argparse.Namespace, command: str) -> None:
    """Require exactly one sample-selection flag for the run command."""

    selection_count = sum(
        [
            bool(getattr(args, "sample_id", None) and str(getattr(args, "sample_id")).strip()),
            bool(getattr(args, "random", False)),
            bool(getattr(args, "expert_random", False)),
        ]
    )
    if selection_count != 1:
        raise ValueError(f"{command} requires exactly one of --sample-id, --random, or --expert-random.")



def _require_sample_id(args: argparse.Namespace, command: str) -> str:
    """Require a sample ID for a stage-specific command."""

    if getattr(args, "random", False) or getattr(args, "expert_random", False):
        raise ValueError(f"{command} requires --sample-id and does not accept --random or --expert-random.")
    sample_id = getattr(args, "sample_id", None)
    if not sample_id or not str(sample_id).strip():
        raise ValueError(f"{command} requires --sample-id.")
    return str(sample_id).strip()



def _print_pipeline_summary(summary: Any) -> None:
    """Print the standard end-of-run summary."""

    output_dir = Path(summary.output_dir)
    artifact_paths = dict(summary.artifact_paths)
    lines = [
        f"Sample ID: {summary.sample_id}",
        f"Original prompt path: {artifact_paths.get('original_prompt_path', output_dir / '01_original' / 'original_prompt.txt')}",
        f"Original CAD code path: {artifact_paths.get('original_code_path', output_dir / '01_original' / 'original_code.py')}",
        f"Original STEP path: {artifact_paths.get('original_step_path', output_dir / '01_original' / 'original.step')}",
        f"Original render folder: {output_dir / '01_original' / 'views'}",
        "",
        f"FEA-ready prompt path: {artifact_paths.get('fea_ready_prompt_path', output_dir / '02_fea_ready' / 'fea_ready_prompt.txt')}",
        f"Load case JSON path: {artifact_paths.get('load_case_path', output_dir / '02_fea_ready' / 'load_case.json')}",
        f"FEA-ready CAD code path: {artifact_paths.get('fea_ready_code_path', output_dir / '02_fea_ready' / 'fea_ready_code.py')}",
        f"FEA-ready STEP path: {artifact_paths.get('fea_ready_step_path', output_dir / '02_fea_ready' / 'fea_ready.step')}",
        f"FEA-ready render folder: {output_dir / '02_fea_ready' / 'views'}",
        "",
        f"Manual FreeCAD instructions: {artifact_paths.get('freecad_instructions_path', output_dir / '04_manual_freecad_fea' / 'freecad_instructions.md')}",
        f"Manual FEA report template: {artifact_paths.get('fea_report_template_path', output_dir / '04_manual_freecad_fea' / 'fea_report.json')}",
        f"Comparison report path: {artifact_paths.get('comparison_after_fea_path', output_dir / '05_post_fea_refinement' / 'comparison_after_fea.md')}",
        f"Run manifest path: {artifact_paths.get('run_manifest_path', output_dir / 'run_manifest.json')}",
    ]
    if summary.failures:
        lines.append("")
        lines.append("Failures:")
        for failure in summary.failures:
            lines.append(f"- {failure}")
    sys.stdout.write("\n".join(lines).rstrip() + "\n")



def _print_mapping(mapping: Mapping[str, Any]) -> None:
    """Print a simple key/value mapping."""

    for key in sorted(mapping.keys()):
        sys.stdout.write(f"{key}: {mapping[key]}\n")


def _format_schema_summary(summary: Mapping[str, Any]) -> str:
    """Render a readable schema summary for the CLI."""

    lines: list[str] = [
        "Schema summary",
        f"Dialect: {summary.get('dialect', 'unknown')}",
        f"Table count: {summary.get('table_count', 0)}",
        "",
    ]
    tables = summary.get("tables") or []
    if not tables:
        lines.append("No tables found.")
        return "\n".join(lines).rstrip() + "\n"

    for table in tables:
        table_name = str(table.get("name", "<unknown>"))
        columns = list(table.get("columns") or [])
        lines.append(f"Table: {table_name} ({len(columns)} columns)")
        lines.extend(_format_column_table(columns))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"



def _format_column_table(columns: Sequence[Mapping[str, Any]]) -> list[str]:
    """Render a simple column table for one schema table."""

    rows: list[list[str]] = []
    for column in columns:
        rows.append(
            [
                str(column.get("name", "")),
                str(column.get("type", "")),
                _yes_no(column.get("nullable", True)),
                _yes_no(column.get("primary_key", False)),
                _format_default(column.get("default")),
            ]
        )

    headers = ["name", "type", "nullable", "pk", "default"]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    header_line = "  " + " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    separator = "  " + "-+-".join("-" * width for width in widths)
    lines = [header_line, separator]
    for row in rows:
        lines.append("  " + " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))
    return lines



def _yes_no(value: Any) -> str:
    """Return a readable yes/no string."""

    return "yes" if bool(value) else "no"



def _format_default(value: Any) -> str:
    """Format a column default value for display."""

    if value is None:
        return "-"
    text = str(value).strip()
    return text or "-"


if __name__ == "__main__":
    raise SystemExit(main())
