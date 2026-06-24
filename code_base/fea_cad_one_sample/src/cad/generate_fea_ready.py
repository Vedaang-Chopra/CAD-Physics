"""Generate FEA-ready CadQuery code for the one-sample workflow."""

from __future__ import annotations

import logging
from importlib import import_module
from pathlib import Path
from typing import Any

from src.config import load_config
from src.cad.execute_cadquery import execute_and_export_cadquery
from src.copied_from_cadcodeverify.db.connections import build_llm_connector
from src.copied_from_cadcodeverify.generation.services.generator import Generator
from src.schemas.config import PipelineConfig

logger = logging.getLogger(__name__)


def generate_fea_ready_code(fea_ready_prompt: str, config: PipelineConfig) -> str:
    """Generate runnable FEA-ready CadQuery code from one prompt."""

    logger.info(
        "generate_fea_ready_code | start | config_name=%s | output_root=%s | prompt_length=%d",
        config.config_name,
        config.output_root,
        len(fea_ready_prompt or ""),
    )
    artifact_dir = _artifact_dir(config)
    raw_response: str | None = None
    try:
        runtime_config = _load_runtime_config(config)
        _ensure_fea_ready_artifacts_can_be_written(artifact_dir, force=config.force)
        generator = Generator(_build_connector(runtime_config), runtime_config)
        raw_response = generator.generate_code_raw(
            prompt=fea_ready_prompt,
            system_instruction=runtime_config.get("generation", {}).get("expert_instruction"),
        )
        code = _validate_raw_response(raw_response)
        _save_fea_ready_code_artifact(artifact_dir, code, force=config.force)
        logger.info(
            "generate_fea_ready_code | done | output_dir=%s | line_count=%d",
            artifact_dir,
            len(code.splitlines()),
        )
        return code
    except Exception:
        _write_failure_artifact(artifact_dir, fea_ready_prompt, raw_response)
        logger.exception(
            "generate_fea_ready_code | failed | config_name=%s | output_root=%s",
            config.config_name,
            config.output_root,
        )
        raise


def _load_runtime_config(config: PipelineConfig) -> dict[str, Any]:
    """Load the runtime YAML config for the current pipeline run."""

    return load_config(config_name=config.config_path.name, config_dir=config.config_path.parent)


def _artifact_dir(config: PipelineConfig) -> Path | None:
    """Return the FEA-ready artifact directory when output storage is enabled."""

    if config.output_root is None:
        return None
    return Path(config.output_root) / "02_fea_ready"


def _ensure_fea_ready_artifacts_can_be_written(artifact_dir: Path | None, *, force: bool) -> None:
    """Refuse to overwrite existing FEA-ready code artifacts unless force is enabled."""

    if artifact_dir is None or force:
        return
    targets = [
        artifact_dir / "fea_ready_code.py",
        artifact_dir / "fea_ready_failure.txt",
    ]
    if any(path.exists() for path in targets):
        raise FileExistsError(
            f"Existing FEA-ready artifacts found in {artifact_dir}. Use force=True to overwrite."
        )


def _build_connector(runtime_config: dict[str, Any]) -> Any:
    """Build the copied LLM connector from config."""

    model_config = runtime_config.get("model", {})
    if not isinstance(model_config, dict):
        raise ValueError("Config model section must be a mapping.")
    return build_llm_connector(model_config)


def _validate_raw_response(raw_response: str) -> str:
    """Import the CadQuery validator lazily and extract runnable code."""

    validator = import_module("src.cad.validate_cad_script")
    return validator.extract_and_validate_cadquery_code(raw_response)


def _save_fea_ready_code_artifact(artifact_dir: Path | None, code: str, *, force: bool) -> None:
    """Persist the generated FEA-ready code when output storage is enabled."""

    if artifact_dir is None:
        return

    artifact_dir.mkdir(parents=True, exist_ok=True)
    code_path = artifact_dir / "fea_ready_code.py"
    if code_path.exists() and not force:
        raise FileExistsError(
            f"Existing FEA-ready code found at {code_path}. Use force=True to overwrite."
        )
    code_path.write_text(code, encoding="utf-8")


def execute_and_export_fea_ready_cadquery(
    code: str,
    output_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    """Execute FEA-ready CadQuery code and export fea_ready STEP/STL artifacts."""

    logger.info(
        "execute_and_export_fea_ready_cadquery | start | output_dir=%s | force=%s",
        output_dir,
        force,
    )
    try:
        result = execute_and_export_cadquery(code, output_dir=output_dir, basename="fea_ready", force=force)
        logger.info(
            "execute_and_export_fea_ready_cadquery | done | step_path=%s | stl_path=%s",
            result.get("step_path"),
            result.get("stl_path"),
        )
        return result
    except Exception:
        logger.exception(
            "execute_and_export_fea_ready_cadquery | failed | output_dir=%s | force=%s",
            output_dir,
            force,
        )
        raise


def _write_failure_artifact(artifact_dir: Path | None, prompt: str, raw_response: str | None) -> None:
    """Write a readable failure artifact for the FEA-ready generation stage."""

    if artifact_dir is None:
        return

    artifact_dir.mkdir(parents=True, exist_ok=True)
    failure_path = artifact_dir / "fea_ready_failure.txt"
    lines = [
        "FEA-ready generation failed.",
        "",
        f"prompt_length: {len(prompt or '')}",
        f"raw_response_length: {len(raw_response or '')}",
        "",
        "prompt:",
        prompt.strip() or "<empty>",
        "",
        "raw_response:",
        (raw_response or "").strip() or "<empty>",
    ]
    failure_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
