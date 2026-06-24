# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/load_data/core/model_config.py
"""Model configuration normalization utilities."""
from __future__ import annotations

from typing import Any, Dict, List


def extract_model_name(model_config: Dict[str, Any]) -> str:
    """Extract a stable model name from a model config dict.

    Looks for ``model``, ``name``, or ``id`` keys in that order.
    """
    for key in ["model", "name", "id"]:
        model_name = model_config.get(key)
        if isinstance(model_name, str) and model_name.strip():
            return model_name.strip()

    raise ValueError(
        "Cannot extract model_name from model config. "
        f"Expected one of ['model', 'name', 'id']; got: {model_config}"
    )


def normalize_model_configs(computation_graph_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize config into a non-empty list of model config dicts.

    Supports both:
    - ``computation_graph.models = [...]``
    - Legacy single-model config stored directly on ``computation_graph``
    """
    raw_models = computation_graph_config.get("models")
    if isinstance(raw_models, list) and raw_models:
        return [dict(model_config) for model_config in raw_models]

    return [
        {
            "model": (
                computation_graph_config.get("model")
                or computation_graph_config.get("name")
                or computation_graph_config.get("id")
                or "unknown"
            ),
            "provider": computation_graph_config.get("provider", "openai"),
            "connection_string": computation_graph_config.get("connection_string"),
            "api_key": computation_graph_config.get("api_key"),
        }
    ]
