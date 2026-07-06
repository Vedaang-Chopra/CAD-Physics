"""Generate the State C post-FEA revision for the one-sample workflow."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, is_dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Mapping

from src.cad.execute_cadquery import execute_and_export_cadquery
from src.config import load_config
from src.copied_from_cadcodeverify.db.connections import build_llm_connector
from src.copied_from_cadcodeverify.generation.services.generator import Generator
from src.fea.manual_report import validate_manual_fea_completion
from src.fea.post_fea_prompt import build_post_fea_prompt
from src.schemas.config import PipelineConfig
from src.schemas.fea import LoadCase, ManualFEAReport, RevisionChangeLog
from src.schemas.pipeline import PostFEARevisionResult

logger = logging.getLogger(__name__)


def revise_code_after_fea(
    fea_revision_code: str,
    load_case: LoadCase,
    fea_report: ManualFEAReport | Mapping[str, Any],
    screenshots: list[Path],
    config: PipelineConfig,
) -> PostFEARevisionResult:
    """Generate the State C revision artifacts after manual FEA evidence exists."""

    logger.info(
        "revise_code_after_fea | start | sample_id=%s | output_root=%s | code_length=%d | screenshot_count=%d",
        load_case.sample_id,
        config.output_root,
        len(fea_revision_code or ""),
        len(screenshots),
    )
    artifact_dir = _post_fea_artifact_dir(config, load_case.sample_id)
    prompt_text = ""
    raw_response: str | None = None
    try:
        report_dict = _as_mapping(fea_report)
        validation = validate_manual_fea_completion(report_dict, screenshots)
        if not validation["is_complete"]:
            raise ValueError(
                "State C blocked: manual FEA evidence is incomplete. "
                f"missing_fields={validation['missing_fields']} missing_evidence_paths={validation['missing_evidence_paths']}"
            )

        runtime_config = _load_runtime_config(config)
        _ensure_post_fea_artifacts_can_be_written(artifact_dir, force=config.force)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        manual_report_path = _manual_report_path(config, load_case.sample_id)

        prompt_text = build_post_fea_prompt(fea_revision_code, load_case, report_dict, screenshots)
        prompt_path = artifact_dir / "post_fea_prompt.txt"
        code_path = artifact_dir / "post_fea_code.py"
        change_log_path = artifact_dir / "post_fea_change_log.json"
        provenance_path = artifact_dir / "provenance.json"

        _write_text_artifact(prompt_path, prompt_text, force=config.force)

        generator = Generator(_build_connector(runtime_config), runtime_config)
        raw_response = generator.generate_code_raw(
            prompt=prompt_text,
            system_instruction=runtime_config.get("generation", {}).get("expert_instruction"),
        )
        code = _validate_raw_response(raw_response)
        _write_text_artifact(code_path, code, force=config.force)

        change_log = _extract_change_log(raw_response=raw_response, fea_report=report_dict, screenshots=screenshots)
        _write_json_artifact(change_log_path, change_log, force=config.force)

        code_hash = _sha256_text(code)
        provenance = _build_provenance(
            load_case=load_case,
            prompt_path=prompt_path,
            code_path=code_path,
            change_log_path=change_log_path,
            manual_report_path=manual_report_path,
            screenshots=screenshots,
            raw_response=raw_response,
            code_hash=code_hash,
            prompt_text=prompt_text,
        )
        _write_json_artifact(provenance_path, provenance, force=config.force)

        result = PostFEARevisionResult(
            sample_id=load_case.sample_id,
            prompt_path=prompt_path,
            load_case_path=_state_b_load_case_path(config, load_case.sample_id),
            manual_report_path=manual_report_path,
            screenshot_paths=screenshots,
            code_path=code_path,
            change_log_path=change_log_path,
            provenance_path=provenance_path,
            step_path=artifact_dir / "post_fea.step",
            stl_path=artifact_dir / "post_fea.stl",
            execution_log_path=artifact_dir / "execution_log.txt",
            view_paths={
                "front": artifact_dir / "views" / "front.png",
                "side": artifact_dir / "views" / "side.png",
                "top": artifact_dir / "views" / "top.png",
                "iso": artifact_dir / "views" / "iso.png",
                "grid": artifact_dir / "views" / "grid.png",
            },
            code_hash_sha256=code_hash,
        )
        logger.info(
            "revise_code_after_fea | done | sample_id=%s | artifact_dir=%s | code_hash=%s",
            load_case.sample_id,
            artifact_dir,
            code_hash,
        )
        return result
    except Exception:
        _write_revision_failure_artifact(artifact_dir, prompt_text, raw_response)
        logger.exception(
            "revise_code_after_fea | failed | sample_id=%s | output_root=%s",
            load_case.sample_id,
            config.output_root,
        )
        raise


def execute_and_export_post_fea_revision_cadquery(
    code: str,
    output_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    """Execute State C CadQuery code and export post_fea STEP/STL artifacts."""

    logger.info(
        "execute_and_export_post_fea_revision_cadquery | start | output_dir=%s | force=%s",
        output_dir,
        force,
    )
    try:
        result = execute_and_export_cadquery(code, output_dir=output_dir, basename="post_fea", force=force)
        logger.info(
            "execute_and_export_post_fea_revision_cadquery | done | step_path=%s | stl_path=%s",
            result.get("step_path"),
            result.get("stl_path"),
        )
        return result
    except Exception:
        logger.exception(
            "execute_and_export_post_fea_revision_cadquery | failed | output_dir=%s | force=%s",
            output_dir,
            force,
        )
        raise


def _as_mapping(report: ManualFEAReport | Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a manual FEA report dataclass or mapping into a dict."""

    if is_dataclass(report):
        return asdict(report)
    return dict(report)


def _post_fea_artifact_dir(config: PipelineConfig, sample_id: str) -> Path:
    """Return the canonical State C artifact directory for one sample."""

    if config.output_root is None:
        raise ValueError("PipelineConfig.output_root is required for State C revision artifacts.")
    return Path(config.output_root) / f"sample_{sample_id}" / "05_post_fea_revision"


def _state_b_load_case_path(config: PipelineConfig, sample_id: str) -> Path:
    """Return the canonical State B load-case path for one sample."""

    if config.output_root is None:
        raise ValueError("PipelineConfig.output_root is required for State C load case lookup.")
    return Path(config.output_root) / f"sample_{sample_id}" / "02_fea_constrained_revision" / "load_case.json"


def _manual_report_path(config: PipelineConfig, sample_id: str) -> Path:
    """Return the canonical manual FEA report path for one sample."""

    if config.output_root is None:
        raise ValueError("PipelineConfig.output_root is required for State C manual report lookup.")
    return Path(config.output_root) / f"sample_{sample_id}" / "04_manual_freecad_fea" / "fea_report.json"


def _ensure_post_fea_artifacts_can_be_written(artifact_dir: Path, *, force: bool) -> None:
    """Refuse to overwrite existing State C artifacts unless force is enabled."""

    if force:
        return
    targets = [
        artifact_dir / "post_fea_prompt.txt",
        artifact_dir / "post_fea_code.py",
        artifact_dir / "post_fea_change_log.json",
        artifact_dir / "provenance.json",
    ]
    if any(path.exists() for path in targets):
        raise FileExistsError(f"Existing State C artifacts found in {artifact_dir}. Use force=True to overwrite.")


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


def _extract_change_log(raw_response: str | None, fea_report: Mapping[str, Any], screenshots: list[Path]) -> dict[str, Any]:
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
                        "sample_id": fea_report.get("sample_id", "unknown"),
                        "source_state": "State B",
                        "target_state": "State C",
                        "preserve_identity": True,
                        "changed_features": change_log,
                        "notes": [],
                    }
        except Exception:
            logger.debug("_extract_change_log | raw response not JSON | sample_id=%s", fea_report.get("sample_id", "unknown"))

    change_log = RevisionChangeLog(
        sample_id=str(fea_report.get("sample_id", "unknown")),
        source_state="State B",
        target_state="State C",
        preserve_identity=True,
        changed_features=[
            {
                "feature": "FEA feedback revision",
                "change_type": "synthesized",
                "reason": "The model response did not include a structured change log; synthesize one from the post-FEA inputs.",
                "expected_effect": "Reduce stress and/or displacement while preserving the original design intent.",
                "screenshot_count": len(screenshots),
            }
        ],
        notes=[
            f"Max von Mises stress: {fea_report.get('max_von_mises_pa')}",
            f"Max displacement: {fea_report.get('max_displacement_mm')}",
            f"Computed safety factor: {fea_report.get('computed_safety_factor')}",
        ],
    )
    return asdict(change_log)


def _build_provenance(
    load_case: LoadCase,
    prompt_path: Path,
    code_path: Path,
    change_log_path: Path,
    manual_report_path: Path,
    screenshots: list[Path],
    raw_response: str | None,
    code_hash: str,
    prompt_text: str,
) -> dict[str, Any]:
    """Build provenance metadata for the State C revision."""

    return {
        "sample_id": load_case.sample_id,
        "source_state": "State B",
        "target_state": "State C",
        "prompt_source": "manual_fea_feedback",
        "prompt_path": str(prompt_path),
        "code_path": str(code_path),
        "change_log_path": str(change_log_path),
        "manual_report_path": str(manual_report_path),
        "screenshot_paths": [str(path) for path in screenshots],
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


def _write_revision_failure_artifact(artifact_dir: Path | None, prompt: str, raw_response: str | None) -> None:
    """Write a readable failure artifact for the State C revision stage."""

    if artifact_dir is None:
        return

    artifact_dir.mkdir(parents=True, exist_ok=True)
    failure_path = artifact_dir / "post_fea_failure.txt"
    lines = [
        "State C revision failed.",
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
