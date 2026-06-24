"""CLI entry point for the one-sample FEA prototype."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Mapping, Sequence
from typing import Any

from src.config import load_config
from src.db.schema_inspection import inspect_schema

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
        help="Overwrite existing outputs when a command writes artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect-schema",
        help="Inspect the configured database schema.",
    )
    inspect_parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        help="Config filename to load.",
    )
    inspect_parser.add_argument(
        "--force",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Overwrite existing outputs when a command writes artifacts.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return an exit code."""

    logger.info("main | start | argv=%s", argv)
    parser = build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        if args.command == "inspect-schema":
            exit_code = _run_inspect_schema(str(args.config), force=bool(getattr(args, "force", False)))
            logger.info("main | done | command=%s | exit_code=%d", args.command, exit_code)
            return exit_code
        raise RuntimeError(f"Unsupported command: {args.command}")
    except SystemExit:
        raise
    except Exception as exc:
        logger.error("main | failed | error=%s", exc)
        sys.stderr.write(f"Error: {exc}\n")
        return 1


def _run_inspect_schema(config_name: str, force: bool = False) -> int:
    """Load the configured DB connection string and print its schema summary."""

    logger.info("inspect-schema | start | config_name=%s | force=%s", config_name, force)
    config = load_config(config_name)
    connection_string = _resolve_connection_string(config)
    summary = inspect_schema(connection_string)
    sys.stdout.write(_format_schema_summary(summary))
    logger.info(
        "inspect-schema | done | config_name=%s | table_count=%s | force=%s",
        config_name,
        summary.get("table_count"),
        force,
    )
    return 0


def _resolve_connection_string(config: Mapping[str, Any]) -> str:
    """Extract and validate the database connection string from config."""

    connection_string = _get_nested_string(config, ("db", "connection_string"))
    if not connection_string:
        connection_string = _get_nested_string(config, ("connection_string",))
    if not connection_string:
        raise ValueError(
            "DB connection string is required. Set CAD_DB_CONNECTION_STRING or db.connection_string."
        )
    if "${" in connection_string:
        raise ValueError(
            "DB connection string is unresolved. Set CAD_DB_CONNECTION_STRING before running inspect-schema."
        )
    return connection_string


def _get_nested_string(config: Mapping[str, Any], path: tuple[str, ...]) -> str:
    """Return a stripped string at the requested mapping path."""

    current: Any = config
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return ""
        current = current[key]
    if not isinstance(current, str):
        return ""
    return current.strip()


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
