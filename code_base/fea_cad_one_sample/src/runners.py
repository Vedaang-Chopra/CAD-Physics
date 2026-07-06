"""Thin runner entry points for the one-sample FEA prototype."""

# pyright: reportMissingImports=false

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.config import load_config
from src.db.schema_inspection import inspect_schema
from src.orchestration.pipeline import (
    build_comparison_stage,
    build_fea_ready_prompt_stage,
    build_manual_fea_stage,
    build_post_fea_stage,
    generate_fea_ready_code_stage,
    execute_fea_ready_stage,
    generate_original_code_stage,
    execute_original_stage,
    prepare_run_context,
    render_fea_ready_stage,
    render_original_stage,
    run_full_pipeline,
    write_original_prompt_stage,
)
from src.schemas.config import PipelineConfig
from src.schemas.pipeline import PipelineSummary

logger = logging.getLogger(__name__)


def inspect_schema_runner(config_name: str) -> dict[str, Any]:
    """Inspect the configured database schema and return a serializable summary."""

    logger.info("inspect_schema_runner | start | config_name=%s", config_name)
    try:
        runtime_config = load_config(config_name, _config_dir())
        connection_string = _resolve_connection_string(runtime_config)
        summary = inspect_schema(connection_string)
        logger.info(
            "inspect_schema_runner | done | config_name=%s | table_count=%s",
            config_name,
            summary.get("table_count"),
        )
        return summary
    except Exception:
        logger.exception("inspect_schema_runner | failed | config_name=%s", config_name)
        raise


def run_full_pipeline_runner(
    config_name: str,
    sample_id: str | None,
    random: bool,
    expert_random: bool,
    force: bool,
) -> PipelineSummary:
    """Run the full pipeline for one selected sample."""

    logger.info(
        "run_full_pipeline_runner | start | config_name=%s | sample_id=%s | random=%s | expert_random=%s | force=%s",
        config_name,
        sample_id,
        random,
        expert_random,
        force,
    )
    try:
        config = _build_pipeline_config(config_name, force=force)
        summary = run_full_pipeline(
            config,
            {
                "sample_id": sample_id,
                "random": random,
                "expert_random": expert_random,
            },
        )
        logger.info(
            "run_full_pipeline_runner | done | sample_id=%s | output_dir=%s",
            summary.sample_id,
            summary.output_dir,
        )
        return summary
    except Exception:
        logger.exception(
            "run_full_pipeline_runner | failed | config_name=%s | sample_id=%s",
            config_name,
            sample_id,
        )
        raise


def state_a_only_runner(config_name: str, sample_id: str | None, random: bool, expert_random: bool, force: bool) -> dict[str, str]:
    """Run the State A pipeline stages for one selected sample."""

    logger.info(
        "state_a_only_runner | start | config_name=%s | sample_id=%s | random=%s | expert_random=%s | force=%s",
        config_name,
        sample_id,
        random,
        expert_random,
        force,
    )
    try:
        context = prepare_run_context(
            _build_pipeline_config(config_name, force=force),
            {
                "sample_id": sample_id,
                "random": random,
                "expert_random": expert_random,
            },
        )
        result: dict[str, str] = {}
        result.update(write_original_prompt_stage(context))
        result.update(generate_original_code_stage(context))
        result.update(execute_original_stage(context))
        result.update(render_original_stage(context))
        logger.info(
            "state_a_only_runner | done | sample_id=%s | files=%s",
            sample_id,
            sorted(result.keys()),
        )
        return result
    except Exception:
        logger.exception(
            "state_a_only_runner | failed | config_name=%s | sample_id=%s",
            config_name,
            sample_id,
        )
        raise


def state_b_only_runner(config_name: str, sample_id: str | None, random: bool, expert_random: bool, force: bool) -> dict[str, str]:
    """Run the State A and State B pipeline stages for one selected sample."""

    logger.info(
        "state_b_only_runner | start | config_name=%s | sample_id=%s | random=%s | expert_random=%s | force=%s",
        config_name,
        sample_id,
        random,
        expert_random,
        force,
    )
    try:
        context = prepare_run_context(
            _build_pipeline_config(config_name, force=force),
            {
                "sample_id": sample_id,
                "random": random,
                "expert_random": expert_random,
            },
        )
        result: dict[str, str] = {}
        result.update(write_original_prompt_stage(context))
        result.update(generate_original_code_stage(context))
        result.update(execute_original_stage(context))
        result.update(render_original_stage(context))
        result.update(build_fea_ready_prompt_stage(context))
        result.update(generate_fea_ready_code_stage(context))
        result.update(execute_fea_ready_stage(context))
        result.update(render_fea_ready_stage(context))
        logger.info(
            "state_b_only_runner | done | sample_id=%s | files=%s",
            sample_id,
            sorted(result.keys()),
        )
        return result
    except Exception:
        logger.exception(
            "state_b_only_runner | failed | config_name=%s | sample_id=%s",
            config_name,
            sample_id,
        )
        raise


def state_c_only_runner(config_name: str, sample_id: str | None, random: bool, expert_random: bool, force: bool) -> dict[str, Any]:
    """Run the State A, State B, and gated State C pipeline stages for one selected sample."""

    logger.info(
        "state_c_only_runner | start | config_name=%s | sample_id=%s | random=%s | expert_random=%s | force=%s",
        config_name,
        sample_id,
        random,
        expert_random,
        force,
    )
    try:
        context = prepare_run_context(
            _build_pipeline_config(config_name, force=force),
            {
                "sample_id": sample_id,
                "random": random,
                "expert_random": expert_random,
            },
        )
        result: dict[str, Any] = {}
        result.update(write_original_prompt_stage(context))
        result.update(generate_original_code_stage(context))
        result.update(execute_original_stage(context))
        result.update(render_original_stage(context))
        result.update(build_fea_ready_prompt_stage(context))
        result.update(generate_fea_ready_code_stage(context))
        result.update(execute_fea_ready_stage(context))
        result.update(render_fea_ready_stage(context))
        result.update(build_manual_fea_stage(context))
        result.update(build_post_fea_stage(context))
        logger.info(
            "state_c_only_runner | done | sample_id=%s | files=%s",
            sample_id,
            sorted(result.keys()),
        )
        return result
    except Exception:
        logger.exception(
            "state_c_only_runner | failed | config_name=%s | sample_id=%s",
            config_name,
            sample_id,
        )
        raise


def render_only_runner(config_name: str, sample_id: str, force: bool) -> dict[str, str]:
    """Render the standard original and FEA-ready view sets for one sample."""

    logger.info(
        "render_only_runner | start | config_name=%s | sample_id=%s | force=%s",
        config_name,
        sample_id,
        force,
    )
    try:
        context = prepare_run_context(_build_pipeline_config(config_name, force=force), {"sample_id": sample_id})
        result: dict[str, str] = {}
        result.update(render_original_stage(context))
        result.update(render_fea_ready_stage(context))
        logger.info(
            "render_only_runner | done | sample_id=%s | files=%s",
            sample_id,
            sorted(result.keys()),
        )
        return result
    except Exception:
        logger.exception(
            "render_only_runner | failed | config_name=%s | sample_id=%s",
            config_name,
            sample_id,
        )
        raise


def build_fea_prompt_only_runner(config_name: str, sample_id: str, force: bool) -> dict[str, str]:
    """Build the load case JSON and FEA-ready prompt for one sample."""

    logger.info(
        "build_fea_prompt_only_runner | start | config_name=%s | sample_id=%s | force=%s",
        config_name,
        sample_id,
        force,
    )
    try:
        context = prepare_run_context(_build_pipeline_config(config_name, force=force), {"sample_id": sample_id})
        result = build_fea_ready_prompt_stage(context)
        logger.info(
            "build_fea_prompt_only_runner | done | sample_id=%s | files=%s",
            sample_id,
            sorted(result.keys()),
        )
        return result
    except Exception:
        logger.exception(
            "build_fea_prompt_only_runner | failed | config_name=%s | sample_id=%s",
            config_name,
            sample_id,
        )
        raise


def build_freecad_instructions_only_runner(config_name: str, sample_id: str, force: bool) -> dict[str, str]:
    """Build the manual FreeCAD FEM instructions and report template."""

    logger.info(
        "build_freecad_instructions_only_runner | start | config_name=%s | sample_id=%s | force=%s",
        config_name,
        sample_id,
        force,
    )
    try:
        context = prepare_run_context(_build_pipeline_config(config_name, force=force), {"sample_id": sample_id})
        if context.load_case is None:
            build_fea_ready_prompt_stage(context)
        result = build_manual_fea_stage(context)
        logger.info(
            "build_freecad_instructions_only_runner | done | sample_id=%s | files=%s",
            sample_id,
            sorted(result.keys()),
        )
        return result
    except Exception:
        logger.exception(
            "build_freecad_instructions_only_runner | failed | config_name=%s | sample_id=%s",
            config_name,
            sample_id,
        )
        raise


def comparison_only_runner(config_name: str, sample_id: str | None, random: bool, expert_random: bool, force: bool) -> dict[str, str]:
    """Build the State A/B comparison artifacts for one selected sample."""

    logger.info(
        "comparison_only_runner | start | config_name=%s | sample_id=%s | random=%s | expert_random=%s | force=%s",
        config_name,
        sample_id,
        random,
        expert_random,
        force,
    )
    try:
        context = prepare_run_context(
            _build_pipeline_config(config_name, force=force),
            {
                "sample_id": sample_id,
                "random": random,
                "expert_random": expert_random,
            },
        )
        result: dict[str, str] = {}
        result.update(write_original_prompt_stage(context))
        result.update(generate_original_code_stage(context))
        result.update(execute_original_stage(context))
        result.update(render_original_stage(context))
        result.update(build_fea_ready_prompt_stage(context))
        result.update(generate_fea_ready_code_stage(context))
        result.update(execute_fea_ready_stage(context))
        result.update(render_fea_ready_stage(context))
        result.update(build_comparison_stage(context))
        logger.info(
            "comparison_only_runner | done | sample_id=%s | files=%s",
            sample_id,
            sorted(result.keys()),
        )
        return result
    except Exception:
        logger.exception(
            "comparison_only_runner | failed | config_name=%s | sample_id=%s",
            config_name,
            sample_id,
        )
        raise


def compare_only_runner(config_name: str, sample_id: str | None, force: bool) -> dict[str, str]:
    """Compatibility alias for the comparison artifacts command."""

    return comparison_only_runner(config_name, sample_id, False, False, force)


def _build_pipeline_config(config_name: str, force: bool) -> PipelineConfig:
    """Build a pipeline config anchored at the module root."""

    module_root = Path(__file__).resolve().parents[1]
    return PipelineConfig(
        config_name=config_name,
        config_path=_config_dir() / config_name,
        output_root=module_root / "outputs",
        force=force,
    )


def _config_dir() -> Path:
    """Return the directory that stores copied runtime configs."""

    return Path(__file__).resolve().parent / "copied_from_cadcodeverify" / "configs"


def _resolve_connection_string(runtime_config: dict[str, Any]) -> str:
    """Extract the DB connection string from a loaded runtime config."""

    connection_string = _nested_string(runtime_config, ("db", "connection_string"))
    if not connection_string:
        connection_string = _nested_string(runtime_config, ("connection_string",))
    if not connection_string:
        raise ValueError("DB connection string is required. Set CAD_DB_CONNECTION_STRING or db.connection_string.")
    if "${" in connection_string:
        raise ValueError("DB connection string is unresolved. Set CAD_DB_CONNECTION_STRING before running.")
    return connection_string


def _nested_string(config: dict[str, Any], path: tuple[str, ...]) -> str:
    """Return a stripped string at a nested mapping path."""

    current: Any = config
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return ""
        current = current[key]
    if not isinstance(current, str):
        return ""
    return current.strip()
