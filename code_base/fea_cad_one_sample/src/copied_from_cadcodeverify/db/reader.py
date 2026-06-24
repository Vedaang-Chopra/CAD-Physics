# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/db/reader.py
from __future__ import annotations

import os
from typing import Any, Mapping, Optional, Sequence, Tuple, Union

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

try:
    from .utilities.db_handler import DBHandler
except ImportError:
    from utilities.db_handler import DBHandler  # type: ignore

QueryParams = Optional[Union[Mapping[str, Any], Sequence[Any]]]

_DB_URL_ENV_VARS = ("CAD_DB_CONNECTION_STRING", "CAD_DATABASE_URL", "DATABASE_URL")


def _connection_string_from_env() -> Optional[str]:
    for env_var in _DB_URL_ENV_VARS:
        value = os.getenv(env_var)
        if value:
            return value
    return None


def _resolve_engine(
    *,
    connection_string: Optional[str] = None,
    db_handler: Optional[DBHandler] = None,
    engine: Optional[Engine] = None,
) -> Tuple[Engine, bool]:
    """Return an engine and whether this utility owns disposal of it."""
    provided_sources = [source is not None for source in (connection_string, db_handler, engine)]
    if sum(provided_sources) > 1:
        raise ValueError("Pass only one of connection_string, db_handler, or engine.")

    if db_handler is not None:
        return db_handler.engine, False

    if engine is not None:
        return engine, False

    resolved_connection_string = connection_string or _connection_string_from_env()
    if not resolved_connection_string:
        raise ValueError(
            "No database connection string provided. Pass connection_string or set "
            "CAD_DB_CONNECTION_STRING, CAD_DATABASE_URL, or DATABASE_URL."
        )

    return create_engine(resolved_connection_string), True


def read_sql_dataframe(
    query: str,
    params: QueryParams = None,
    *,
    connection_string: Optional[str] = None,
    db_handler: Optional[DBHandler] = None,
    engine: Optional[Engine] = None,
) -> pd.DataFrame:
    """
    Execute a parameterized SQL query and return the result as a DataFrame.

    The caller owns the SQL text; this helper centralizes engine selection,
    connection handling, and DataFrame materialization.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty SQL string.")

    resolved_engine, dispose_engine = _resolve_engine(
        connection_string=connection_string,
        db_handler=db_handler,
        engine=engine,
    )

    try:
        with resolved_engine.connect() as connection:
            return pd.read_sql_query(text(query), connection, params=params)
    finally:
        if dispose_engine:
            resolved_engine.dispose()
