"""Inspect database schema for the one-sample FEA prototype."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from sqlalchemy import create_engine, inspect

logger = logging.getLogger(__name__)


def inspect_schema(connection_string: str) -> dict[str, Any]:
    """Inspect DB tables and columns and return a serializable summary."""

    has_connection_string = bool(connection_string and connection_string.strip())
    logger.info(
        "inspect_schema | start | connection_string_provided=%s",
        has_connection_string,
    )
    if not isinstance(connection_string, str) or not connection_string.strip():
        raise ValueError("connection_string must be a non-empty database URL.")

    engine = create_engine(connection_string)
    try:
        inspector = inspect(engine)
        table_names = sorted(str(name) for name in inspector.get_table_names())
        tables = [_summarize_table(inspector, table_name) for table_name in table_names]
        result = {
            "dialect": getattr(engine.dialect, "name", "unknown"),
            "table_count": len(tables),
            "tables": tables,
        }
        logger.info(
            "inspect_schema | done | dialect=%s | table_count=%d",
            result["dialect"],
            result["table_count"],
        )
        return result
    except Exception:
        logger.exception(
            "inspect_schema | failed | connection_string_provided=%s",
            has_connection_string,
        )
        raise
    finally:
        engine.dispose()


def _summarize_table(inspector: Any, table_name: str) -> dict[str, Any]:
    """Summarize one table from a SQLAlchemy inspector."""

    columns = inspector.get_columns(table_name)
    column_summaries = [_summarize_column(column) for column in columns]
    return {
        "name": table_name,
        "column_count": len(column_summaries),
        "columns": column_summaries,
    }


def _summarize_column(column: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a SQLAlchemy column mapping into serializable metadata."""

    column_type = column.get("type")
    return {
        "name": column.get("name"),
        "type": str(column_type) if column_type is not None else None,
        "nullable": bool(column.get("nullable", True)),
        "default": column.get("default"),
        "primary_key": bool(column.get("primary_key", False)),
    }
