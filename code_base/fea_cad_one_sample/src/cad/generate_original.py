"""Generate baseline CadQuery code for the selected expert prompt."""

from __future__ import annotations

import json
import logging
from importlib import import_module
from pathlib import Path
from typing import Any

from src.config import load_config
from src.copied_from_cadcodeverify.db.connections import build_llm_connector
from src.copied_from_cadcodeverify.generation.services.generator import Generator
from src.schemas.config import PipelineConfig
from src.schemas.sample import CADSample

logger = logging.getLogger(__name__)


def generate_original_code(sample: CADSample, config: PipelineConfig) -> str:
    """Generate runnable baseline CadQuery code from one sample prompt."""

    logger.info(
        "generate_original_code | start | sample_id=%s | config_name=%s",
        sample.sample_id,
        config.config_name,
    )
    try:
        runtime_config = _load_runtime_config(config)
        artifact_dir = _artifact_dir(sample, config)
        if artifact_dir is not None:
            _ensure_original_artifacts_can_be_written(artifact_dir, force=config.force)
        generator = Generator(_build_connector(runtime_config), runtime_config)
        raw_response = generator.generate_code_raw(
            prompt=sample.prompt,
            system_instruction=runtime_config.get("generation", {}).get("expert_instruction"),
        )
        code = _validate_raw_response(raw_response)
        _save_artifacts(sample, config, code=code, raw_response=raw_response, force=config.force)
        logger.info(
            "generate_original_code | done | sample_id=%s | line_count=%d",
            sample.sample_id,
            len(code.splitlines()),
        )
        return code
    except Exception:
        logger.exception(
            "generate_original_code | failed | sample_id=%s | config_name=%s",
            sample.sample_id,
            config.config_name,
        )
        raise


def _load_runtime_config(config: PipelineConfig) -> dict[str, Any]:
    """Load the runtime YAML config for the current pipeline run."""

    return load_config(config_name=config.config_path.name, config_dir=config.config_path.parent)


def _artifact_dir(sample: CADSample, config: PipelineConfig) -> Path | None:
    """Return the original-artifact directory for the current sample."""

    if config.output_root is None:
        return None
    return Path(config.output_root) / f"sample_{sample.sample_id}" / "01_original"


def _ensure_original_artifacts_can_be_written(artifact_dir: Path, *, force: bool) -> None:
    """Refuse to overwrite existing original-artifact outputs unless force is enabled."""

    if force:
        return
    existing_paths = [
        artifact_dir / "original_code.py",
        artifact_dir / "original_raw_response.txt",
        artifact_dir / "metadata.json",
    ]
    if any(path.exists() for path in existing_paths):
        raise FileExistsError(
            f"Existing original artifacts found in {artifact_dir}. Use force=True to overwrite."
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


def _save_artifacts(
    sample: CADSample,
    config: PipelineConfig,
    *,
    code: str,
    raw_response: str,
    force: bool,
) -> None:
    """Persist generated source and raw response when an output root is configured."""

    sample_dir = _artifact_dir(sample, config)
    if sample_dir is None:
        return

    _ensure_original_artifacts_can_be_written(sample_dir, force=force)
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "original_code.py").write_text(code, encoding="utf-8")
    (sample_dir / "original_raw_response.txt").write_text(raw_response, encoding="utf-8")
    (sample_dir / "metadata.json").write_text(
        json.dumps(
            {
                "sample_id": sample.sample_id,
                "prompt_variant": sample.prompt_variant,
                "source": sample.source,
                "raw_response_path": str(sample_dir / "original_raw_response.txt"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
