# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/load_data/services/connections.py
"""LLM connector and database connection utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .paths import ensure_code_base_on_path


def build_llm_connector(model_config: Dict[str, Any]):
    """Instantiate ``LLMConnector`` from a normalized model config dict.

    The fallback import depends on ``ensure_code_base_on_path`` to bootstrap
    the project import path.
    """
    try:
        from utils.llm.llm import LLMConnector
    except ImportError:
        ensure_code_base_on_path(start_path=Path(__file__).resolve())
        from utils.llm.llm import LLMConnector

    return LLMConnector(
        model=model_config.get("model") or model_config.get("name") or "unknown",
        provider=model_config.get("provider", "openai"),
        api_key=model_config.get("api_key"),
        connection_string=model_config.get("connection_string"),
    )


def connect_db(config: Dict[str, Any]):
    """Open a psycopg2 connection from the loaded project config."""
    import psycopg2

    return psycopg2.connect(config["db"]["connection_string"])
