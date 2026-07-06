"""Generate FEA-ready CadQuery code for the one-sample workflow."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from importlib import import_module
from pathlib import Path
from typing import Any

from src.cad.execute_cadquery import execute_and_export_cadquery
from src.config import load_config
from src.prompts.build_fea_prompt import build_fea_prompt
from src.schemas.config import PipelineConfig
from src.schemas.fea import LoadCase, RevisionChangeLog, SelectorHints
from src.schemas.pipeline import FEARevisionResult
from src.copied_from_cadcodeverify.db.connections import build_llm_connector
from src.copied_from_cadcodeverify.generation.services.generator import Generator

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


def revise_code_for_fea(
    original_prompt: str,
    original_code: str,
    load_case: LoadCase,
    selector_hints: SelectorHints,
    config: PipelineConfig,
) -> FEARevisionResult:
    """Generate the State B revision artifacts for one sample."""

    logger.info(
        "revise_code_for_fea | start | sample_id=%s | output_root=%s | prompt_length=%d | code_length=%d",
        load_case.sample_id,
        config.output_root,
        len(original_prompt or ""),
        len(original_code or ""),
    )
    artifact_dir = _revision_artifact_dir(config, load_case.sample_id)
    prompt_text = ""
    raw_response: str | None = None
    try:
        runtime_config = _load_runtime_config(config)
        _ensure_revision_artifacts_can_be_written(artifact_dir, force=config.force)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        prompt_text = build_fea_prompt(original_prompt, original_code, load_case, selector_hints)
        prompt_path = artifact_dir / "fea_revision_prompt.txt"
        load_case_path = artifact_dir / "load_case.json"
        selector_hints_path = artifact_dir / "selector_hints.json"
        code_path = artifact_dir / "fea_revision_code.py"
        change_log_path = artifact_dir / "fea_revision_change_log.json"
        provenance_path = artifact_dir / "provenance.json"

        _write_text_artifact(prompt_path, prompt_text, force=config.force)
        _write_json_artifact(load_case_path, asdict(load_case), force=config.force)
        _write_json_artifact(selector_hints_path, asdict(selector_hints), force=config.force)

        generator = Generator(_build_connector(runtime_config), runtime_config)
        raw_response = generator.generate_code_raw(
            prompt=prompt_text,
            system_instruction=runtime_config.get("generation", {}).get("expert_instruction"),
        )
        code = _validate_raw_response(raw_response)
        _write_text_artifact(code_path, code, force=config.force)

        change_log = _extract_revision_change_log(
            raw_response=raw_response,
            original_prompt=original_prompt,
            original_code=original_code,
            load_case=load_case,
            selector_hints=selector_hints,
        )
        _write_json_artifact(change_log_path, change_log, force=config.force)

        code_hash = _sha256_text(code)
        provenance = _build_revision_provenance(
            load_case=load_case,
            prompt_path=prompt_path,
            code_path=code_path,
            change_log_path=change_log_path,
            selector_hints_path=selector_hints_path,
            raw_response=raw_response,
            code_hash=code_hash,
            prompt_text=prompt_text,
        )
        _write_json_artifact(provenance_path, provenance, force=config.force)

        result = FEARevisionResult(
            sample_id=load_case.sample_id,
            prompt_path=prompt_path,
            load_case_path=load_case_path,
            selector_hints_path=selector_hints_path,
            code_path=code_path,
            change_log_path=change_log_path,
            provenance_path=provenance_path,
            step_path=artifact_dir / "fea_revision.step",
            stl_path=artifact_dir / "fea_revision.stl",
            execution_log_path=artifact_dir / "execution_log.txt",
            view_paths={
                "front": artifact_dir / "views" / "front.png",
                "side": artifact_dir / "views" / "side.png",
                "top": artifact_dir / "views" / "top.png",
                "iso": artifact_dir / "views" / "iso.png",
                "grid": artifact_dir / "views" / "grid.png",
                "annotated_support_load": artifact_dir / "views" / "annotated_support_load.png",
            },
            code_hash_sha256=code_hash,
        )
        logger.info(
            "revise_code_for_fea | done | sample_id=%s | artifact_dir=%s | code_hash=%s",
            load_case.sample_id,
            artifact_dir,
            code_hash,
        )
        return result
    except Exception:
        _write_revision_failure_artifact(artifact_dir, prompt_text, raw_response)
        logger.exception(
            "revise_code_for_fea | failed | sample_id=%s | output_root=%s",
            load_case.sample_id,
            config.output_root,
        )
        raise


def execute_and_export_fea_revision_cadquery(
    code: str,
    output_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    """Execute State B CadQuery code and export fea_revision STEP/STL artifacts."""

    logger.info(
        "execute_and_export_fea_revision_cadquery | start | output_dir=%s | force=%s",
        output_dir,
        force,
    )
    try:
        result = execute_and_export_cadquery(code, output_dir=output_dir, basename="fea_revision", force=force)
        logger.info(
            "execute_and_export_fea_revision_cadquery | done | step_path=%s | stl_path=%s",
            result.get("step_path"),
            result.get("stl_path"),
        )
        return result
    except Exception:
        logger.exception(
            "execute_and_export_fea_revision_cadquery | failed | output_dir=%s | force=%s",
            output_dir,
            force,
        )
        raise


def _revision_artifact_dir(config: PipelineConfig, sample_id: str) -> Path:
    """Return the canonical State B artifact directory for one sample."""

    if config.output_root is None:
        raise ValueError("PipelineConfig.output_root is required for State B revision artifacts.")
    return Path(config.output_root) / f"sample_{sample_id}" / "02_fea_constrained_revision"


def _ensure_revision_artifacts_can_be_written(artifact_dir: Path, *, force: bool) -> None:
    """Refuse to overwrite existing State B revision artifacts unless force is enabled."""

    if force:
        return
    targets = [
        artifact_dir / "fea_revision_prompt.txt",
        artifact_dir / "load_case.json",
        artifact_dir / "selector_hints.json",
        artifact_dir / "fea_revision_code.py",
        artifact_dir / "fea_revision_change_log.json",
        artifact_dir / "provenance.json",
    ]
    if any(path.exists() for path in targets):
        raise FileExistsError(f"Existing revision artifacts found in {artifact_dir}. Use force=True to overwrite.")


def _write_text_artifact(output_path: Path, text: str, *, force: bool) -> None:
    """Write a text artifact without overwriting unless force is enabled."""

    if output_path.exists() and not force:
        raise FileExistsError(f"Existing artifact found at {output_path}. Use force=True to overwrite.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text((text or "").rstrip() + "\n", encoding="utf-8")


def _write_json_artifact(output_path: Path, payload: Any, *, force: bool) -> None:
    """Write a JSON artifact without overwriting unless force is enabled."""

    if output_path.exists() and not force:
        raise FileExistsError(f"Existing artifact found at {output_path}. Use force=True to overwrite.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _extract_revision_change_log(
    raw_response: str | None,
    original_prompt: str,
    original_code: str,
    load_case: LoadCase,
    selector_hints: SelectorHints,
) -> dict[str, Any]:
    """Extract a machine-readable change log from the model output or synthesize one."""

    if raw_response:
        try:
            payload = json.loads(raw_response)
            if isinstance(payload, dict):
                change_log = payload.get("change_log") or payload.get("revision_change_log")
                if isinstance(change_log, dict):
                    return change_log
                if isinstance(change_log, list):
                    return {
                        "sample_id": load_case.sample_id,
                        "source_state": "State A",
                        "target_state": "State B",
                        "preserve_identity": True,
                        "changed_features": change_log,
                        "notes": [],
                    }
        except Exception:
            logger.debug(
                "_extract_revision_change_log | raw response not JSON | sample_id=%s",
                load_case.sample_id,
            )

    change_log = RevisionChangeLog(
        sample_id=load_case.sample_id,
        source_state="State A",
        target_state="State B",
        preserve_identity=True,
        changed_features=[
            {
                "feature": "FEA revision",
                "change_type": "synthesized",
                "reason": "The model response did not include a structured change log; synthesize one from the revision inputs.",
                "expected_effect": "Improve stiffness, meshability, and support/load clarity while preserving identity.",
                "selector_hints": asdict(selector_hints),
            }
        ],
        notes=[
            f"Original prompt length: {len(original_prompt or '')}",
            f"Original code length: {len(original_code or '')}",
        ],
    )
    return asdict(change_log)


def _build_revision_provenance(
    load_case: LoadCase,
    prompt_path: Path,
    code_path: Path,
    change_log_path: Path,
    selector_hints_path: Path,
    raw_response: str | None,
    code_hash: str,
    prompt_text: str,
) -> dict[str, Any]:
    """Build provenance metadata for the State B revision."""

    return {
        "sample_id": load_case.sample_id,
        "source_state": "State A",
        "target_state": "State B",
        "prompt_source": "database_original",
        "prompt_path": str(prompt_path),
        "code_path": str(code_path),
        "change_log_path": str(change_log_path),
        "selector_hints_path": str(selector_hints_path),
        "code_hash_sha256": code_hash,
        "prompt_sha256": _sha256_text(prompt_text),
        "raw_response_sha256": _sha256_text(raw_response or ""),
        "code_line_count": len(_read_text(code_path).splitlines()),
    }


def _sha256_text(text: str) -> str:
    """Return the SHA-256 hash for a text payload."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_text(path: Path) -> str:
    """Read UTF-8 text from disk."""

    return Path(path).read_text(encoding="utf-8")


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


def _write_revision_failure_artifact(artifact_dir: Path | None, prompt: str, raw_response: str | None) -> None:
    """Write a readable failure artifact for the State B revision stage."""

    if artifact_dir is None:
        return

    artifact_dir.mkdir(parents=True, exist_ok=True)
    failure_path = artifact_dir / "fea_revision_failure.txt"
    lines = [
        "State B revision failed.",
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
