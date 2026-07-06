# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/load_data/services/connections.py
"""LLM connector and database connection utilities."""
from __future__ import annotations

from typing import Any, Dict

from ..llm.llm import LLMConnector


def build_llm_connector(model_config: Dict[str, Any]):
    """Instantiate ``LLMConnector`` from a normalized model config dict."""

    return LLMConnector(
        model=_resolve_model_name(model_config),
        provider=model_config.get("provider", "openai"),
        api_key=model_config.get("api_key"),
        connection_string=model_config.get("connection_string"),
    )


def _resolve_model_name(model_config: Dict[str, Any]) -> str:
    """Choose the real model identifier from supported config keys."""

    for key in ("id", "model", "name", "slug"):
        value = model_config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def connect_db(config: Dict[str, Any]):
    """Open a psycopg2 connection from the loaded project config."""
    import psycopg2

    return psycopg2.connect(config["db"]["connection_string"])
