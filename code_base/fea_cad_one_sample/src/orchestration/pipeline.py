"""Pipeline orchestration for the one-sample FEA prototype."""

# pyright: reportMissingImports=false

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

from src.cad.execute_cadquery import execute_and_export_cadquery
from src.cad.generate_fea_ready import execute_and_export_fea_revision_cadquery, revise_code_for_fea
from src.cad.post_fea_revision import execute_and_export_post_fea_revision_cadquery, revise_code_after_fea
from src.cad.generate_original import generate_original_code
from src.config import load_config
from src.db.load_sample import load_sample
from src.fea.freecad_manual_instructions import write_freecad_instructions
from src.fea.manual_report import required_manual_fea_evidence_paths, write_manual_fea_report_template
from src.fea.post_fea_prompt import validate_post_fea_inputs
from src.prompts.build_fea_prompt import build_fea_prompt
from src.reports.build_comparison_report import build_comparison_artifacts
from src.schemas.config import PipelineConfig
from src.schemas.fea import LoadCase, SelectorHints
from src.schemas.pipeline import PipelineSummary
from src.schemas.sample import CADSample
from src.visualization.compare_views import build_side_by_side_comparison
from src.visualization.render_views import render_support_load_annotation, render_views

from .manifest import (
    append_run_failure,
    finalize_run_manifest,
    initialize_run_manifest,
    update_run_manifest,
    write_run_manifest,
)

logger = logging.getLogger(__name__)

STAGE_RESOLVE_CONFIG = "resolve_config"
STAGE_INSPECT_SCHEMA = "inspect_schema"
STAGE_LOAD_SAMPLE = "load_sample"
STAGE_SAVE_ORIGINAL_PROMPT = "save_original_prompt"
STAGE_GENERATE_ORIGINAL = "generate_original_code"
STAGE_EXECUTE_ORIGINAL = "execute_original_cadquery"
STAGE_RENDER_ORIGINAL = "render_original_views"
STAGE_BUILD_FEA_READY = "build_fea_ready_prompt"
STAGE_GENERATE_FEA_READY = "generate_fea_ready_code"
STAGE_EXECUTE_FEA_READY = "execute_fea_ready_cadquery"
STAGE_RENDER_FEA_READY = "render_fea_ready_views"
STAGE_BUILD_COMPARISON = "build_comparison_artifacts"
STAGE_BUILD_MANUAL_FEA = "write_manual_fea_artifacts"
STAGE_BUILD_POST_FEA = "write_post_fea_artifacts"
STAGE_WRITE_MANIFEST = "write_run_manifest"


@dataclass(slots=True)
class PipelineContext:
    """Mutable state passed through the pipeline stages."""

    config: PipelineConfig
    selection: dict[str, Any]
    runtime_config: dict[str, Any]
    connection_string: str
    sample: CADSample
    sample_output_dir: Path
    original_dir: Path
    fea_ready_dir: Path
    comparison_dir: Path
    manual_dir: Path
    post_fea_dir: Path
    manifest_path: Path
    original_prompt: str = ""
    fea_ready_prompt: str = ""
    load_case: LoadCase | None = None
    selector_hints: SelectorHints | None = None
    original_code: str = ""
    fea_ready_code: str = ""
    fea_revision_code: str = ""
    stage_statuses: dict[str, str] = field(default_factory=dict)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    failures: list[dict[str, Any]] = field(default_factory=list)


def prepare_run_context(config: PipelineConfig, selection: Mapping[str, Any]) -> PipelineContext:
    """Resolve config, DB connection details, sample selection, and output paths."""

    logger.info(
        "prepare_run_context | start | config_name=%s | selection_keys=%s",
        config.config_name,
        sorted(selection.keys()),
    )
    try:
        normalized_selection = _normalize_selection(selection)
        runtime_config = load_config(config.config_name, config.config_path.parent)
        connection_string = _resolve_connection_string(runtime_config)
        sample = load_sample(connection_string, **normalized_selection)
        sample_output_dir = Path(config.output_root) / f"sample_{sample.sample_id}"
        context = PipelineContext(
            config=config,
            selection=normalized_selection,
            runtime_config=runtime_config,
            connection_string=connection_string,
            sample=sample,
            sample_output_dir=sample_output_dir,
            original_dir=sample_output_dir / "01_dataset_original",
            fea_ready_dir=sample_output_dir / "02_fea_constrained_revision",
            comparison_dir=sample_output_dir / "03_comparison",
            manual_dir=sample_output_dir / "04_manual_freecad_fea",
            post_fea_dir=sample_output_dir / "05_post_fea_revision",
            manifest_path=sample_output_dir / "run_manifest.json",
        )
        logger.info(
            "prepare_run_context | done | sample_id=%s | sample_output_dir=%s",
            sample.sample_id,
            sample_output_dir,
        )
        return context
    except Exception:
        logger.exception(
            "prepare_run_context | failed | config_name=%s | selection_keys=%s",
            config.config_name,
            sorted(selection.keys()),
        )
        raise


def write_original_prompt_stage(context: PipelineContext) -> dict[str, str]:
    """Write the original prompt artifact for the selected sample."""

    logger.info(
        "write_original_prompt_stage | start | sample_id=%s | output_dir=%s",
        context.sample.sample_id,
        context.original_dir,
    )
    try:
        output_path = context.original_dir / "original_prompt.txt"
        _write_text_artifact(output_path, context.sample.prompt, force=context.config.force)
        context.original_prompt = context.sample.prompt
        result = {"original_prompt_path": str(output_path)}
        context.artifact_paths.update(result)
        logger.info(
            "write_original_prompt_stage | done | sample_id=%s | output_path=%s",
            context.sample.sample_id,
            output_path,
        )
        return result
    except Exception:
        logger.exception(
            "write_original_prompt_stage | failed | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.original_dir,
        )
        raise


def generate_original_code_stage(context: PipelineContext) -> dict[str, str]:
    """Generate and persist the baseline CadQuery code for the selected sample."""

    logger.info(
        "generate_original_code_stage | start | sample_id=%s | output_root=%s",
        context.sample.sample_id,
        context.config.output_root,
    )
    try:
        code = generate_original_code(context.sample, context.config)
        context.original_code = code
        result = {
            "original_prompt_path": str(context.original_dir / "original_prompt.txt"),
            "database_original_code_path": str(context.original_dir / "database_original_code.py"),
            "original_metadata_path": str(context.original_dir / "metadata.json"),
            "original_provenance_path": str(context.original_dir / "provenance.json"),
        }
        context.artifact_paths.update(result)
        logger.info(
            "generate_original_code_stage | done | sample_id=%s | line_count=%d",
            context.sample.sample_id,
            len(code.splitlines()),
        )
        return result
    except Exception:
        logger.exception(
            "generate_original_code_stage | failed | sample_id=%s | output_root=%s",
            context.sample.sample_id,
            context.config.output_root,
        )
        raise


def execute_original_stage(context: PipelineContext) -> dict[str, str]:
    """Execute the baseline CadQuery code and export original STEP/STL artifacts."""

    logger.info(
        "execute_original_stage | start | sample_id=%s | output_dir=%s",
        context.sample.sample_id,
        context.original_dir,
    )
    try:
        code = _require_code(context.original_code, context.original_dir / "original_code.py")
        result = execute_and_export_cadquery(code, output_dir=context.original_dir, basename="original", force=context.config.force)
        artifact_paths = {
            "original_step_path": str(context.original_dir / "original.step"),
            "original_stl_path": str(context.original_dir / "original.stl"),
            "original_execution_log_path": str(context.original_dir / "execution_log.txt"),
        }
        context.artifact_paths.update(artifact_paths)
        logger.info(
            "execute_original_stage | done | sample_id=%s | step_path=%s | stl_path=%s",
            context.sample.sample_id,
            result.get("step_path"),
            result.get("stl_path"),
        )
        return artifact_paths
    except Exception:
        logger.exception(
            "execute_original_stage | failed | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.original_dir,
        )
        raise


def render_original_stage(context: PipelineContext) -> dict[str, str]:
    """Render the standard original geometry views."""

    logger.info(
        "render_original_stage | start | sample_id=%s | output_dir=%s",
        context.sample.sample_id,
        context.original_dir,
    )
    try:
        stl_path = context.original_dir / "original.stl"
        views_dir = context.original_dir / "views"
        result = render_views(stl_path, views_dir, force=context.config.force)
        artifact_paths = {f"original_view_{name}_path": path for name, path in result.items()}
        context.artifact_paths.update(artifact_paths)
        logger.info(
            "render_original_stage | done | sample_id=%s | views=%s",
            context.sample.sample_id,
            sorted(result.keys()),
        )
        return artifact_paths
    except Exception:
        logger.exception(
            "render_original_stage | failed | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.original_dir,
        )
        raise


def build_fea_ready_prompt_stage(context: PipelineContext) -> dict[str, str]:
    """Write the State B revision prompt and its supporting artifacts."""

    logger.info(
        "build_fea_ready_prompt_stage | start | sample_id=%s | output_dir=%s",
        context.sample.sample_id,
        context.fea_ready_dir,
    )
    try:
        context.fea_ready_dir.mkdir(parents=True, exist_ok=True)
        original_prompt = _ensure_original_prompt(context)
        original_code = _ensure_original_code(context)
        load_case = _build_state_b_load_case(context.sample.sample_id)
        selector_hints = _build_state_b_selector_hints(context.sample.sample_id)
        revision_result = revise_code_for_fea(
            original_prompt=original_prompt,
            original_code=original_code,
            load_case=load_case,
            selector_hints=selector_hints,
            config=context.config,
        )
        context.load_case = load_case
        context.selector_hints = selector_hints
        context.fea_ready_prompt = _read_text(revision_result.prompt_path)
        context.fea_revision_code = _read_text(revision_result.code_path)
        artifact_paths = {
            "load_case_path": str(revision_result.load_case_path),
            "selector_hints_path": str(revision_result.selector_hints_path),
            "fea_revision_prompt_path": str(revision_result.prompt_path),
            "fea_revision_code_path": str(revision_result.code_path),
            "fea_revision_change_log_path": str(revision_result.change_log_path),
            "fea_revision_provenance_path": str(revision_result.provenance_path),
        }
        context.artifact_paths.update(artifact_paths)
        logger.info(
            "build_fea_ready_prompt_stage | done | sample_id=%s | prompt_path=%s | code_path=%s",
            context.sample.sample_id,
            revision_result.prompt_path,
            revision_result.code_path,
        )
        return artifact_paths
    except Exception:
        logger.exception(
            "build_fea_ready_prompt_stage | failed | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.fea_ready_dir,
        )
        raise


def generate_fea_ready_code_stage(context: PipelineContext) -> dict[str, str]:
    """Load the State B CadQuery code artifact into memory."""

    logger.info(
        "generate_fea_ready_code_stage | start | sample_id=%s | output_dir=%s",
        context.sample.sample_id,
        context.fea_ready_dir,
    )
    try:
        if not context.fea_ready_prompt:
            context.fea_ready_prompt = _ensure_fea_prompt(context)
        code_path = context.fea_ready_dir / "fea_revision_code.py"
        if not code_path.exists():
            raise FileNotFoundError(f"State B code not found: {code_path}")
        context.fea_revision_code = _read_text(code_path)
        result = {"fea_revision_code_path": str(code_path)}
        context.artifact_paths.update(result)
        logger.info(
            "generate_fea_ready_code_stage | done | sample_id=%s | line_count=%d",
            context.sample.sample_id,
            len(context.fea_revision_code.splitlines()),
        )
        return result
    except Exception:
        logger.exception(
            "generate_fea_ready_code_stage | failed | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.fea_ready_dir,
        )
        raise


def execute_fea_ready_stage(context: PipelineContext) -> dict[str, str]:
    """Execute the State B CadQuery code and export STEP/STL artifacts."""

    logger.info(
        "execute_fea_ready_stage | start | sample_id=%s | output_dir=%s",
        context.sample.sample_id,
        context.fea_ready_dir,
    )
    try:
        code = _require_code(context.fea_revision_code, context.fea_ready_dir / "fea_revision_code.py")
        result = execute_and_export_fea_revision_cadquery(code, output_dir=context.fea_ready_dir, force=context.config.force)
        artifact_paths = {
            "fea_revision_step_path": str(context.fea_ready_dir / "fea_revision.step"),
            "fea_revision_stl_path": str(context.fea_ready_dir / "fea_revision.stl"),
            "fea_revision_execution_log_path": str(context.fea_ready_dir / "execution_log.txt"),
        }
        context.artifact_paths.update(artifact_paths)
        logger.info(
            "execute_fea_ready_stage | done | sample_id=%s | step_path=%s | stl_path=%s",
            context.sample.sample_id,
            result.get("step_path"),
            result.get("stl_path"),
        )
        return artifact_paths
    except Exception:
        logger.exception(
            "execute_fea_ready_stage | failed | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.fea_ready_dir,
        )
        raise


def render_fea_ready_stage(context: PipelineContext) -> dict[str, str]:
    """Render the State B geometry views and support/load annotation."""

    logger.info(
        "render_fea_ready_stage | start | sample_id=%s | output_dir=%s",
        context.sample.sample_id,
        context.fea_ready_dir,
    )
    try:
        stl_path = context.fea_ready_dir / "fea_revision.stl"
        views_dir = context.fea_ready_dir / "views"
        result = render_views(stl_path, views_dir, force=context.config.force)
        if context.selector_hints is None:
            context.selector_hints = _load_selector_hints(context.fea_ready_dir / "selector_hints.json")
        annotated_path = render_support_load_annotation(
            stl_path,
            views_dir / "annotated_support_load.png",
            context.selector_hints,
            force=context.config.force,
        )
        artifact_paths = {f"fea_revision_view_{name}_path": path for name, path in result.items()}
        artifact_paths["fea_revision_view_annotated_support_load_path"] = str(annotated_path)
        context.artifact_paths.update(artifact_paths)
        logger.info(
            "render_fea_ready_stage | done | sample_id=%s | views=%s",
            context.sample.sample_id,
            sorted(result.keys()) + ["annotated_support_load"],
        )
        return artifact_paths
    except Exception:
        logger.exception(
            "render_fea_ready_stage | failed | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.fea_ready_dir,
        )
        raise


def build_comparison_stage(context: PipelineContext) -> dict[str, str]:
    """Write the view-comparison image and markdown comparison files."""

    logger.info(
        "build_comparison_stage | start | sample_id=%s | output_dir=%s",
        context.sample.sample_id,
        context.comparison_dir,
    )
    try:
        original_views_dir = context.original_dir / "views"
        fea_views_dir = context.fea_ready_dir / "views"
        original_prompt = _ensure_original_prompt(context)
        fea_ready_prompt = _ensure_fea_prompt(context)
        context.comparison_dir.mkdir(parents=True, exist_ok=True)
        side_by_side_path = build_side_by_side_comparison(
            original_views_dir,
            fea_views_dir,
            context.comparison_dir / "side_by_side.png",
            force=context.config.force,
        )
        markdown_paths = build_comparison_artifacts(
            original_prompt=original_prompt,
            fea_prompt=fea_ready_prompt,
            output_dir=context.comparison_dir,
            notes={
                "sample_id": context.sample.sample_id,
                "original_step": str(context.original_dir / "original.step"),
                "fea_ready_step": str(context.fea_ready_dir / "fea_ready.step"),
                "why the change happened": "Improve meshability and manual FEA readiness.",
            },
            force=context.config.force,
        )
        artifact_paths = {
            "comparison_side_by_side_path": str(side_by_side_path),
            "comparison_prompt_diff_path": markdown_paths["prompt_diff"],
            "comparison_geometry_diff_notes_path": markdown_paths["geometry_diff_notes"],
        }
        context.artifact_paths.update(artifact_paths)
        logger.info(
            "build_comparison_stage | done | sample_id=%s | output_path=%s",
            context.sample.sample_id,
            side_by_side_path,
        )
        return artifact_paths
    except Exception:
        logger.exception(
            "build_comparison_stage | failed | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.comparison_dir,
        )
        raise


def build_manual_fea_stage(context: PipelineContext) -> dict[str, str]:
    """Write the manual FreeCAD FEM instruction and report template files."""

    logger.info(
        "build_manual_fea_stage | start | sample_id=%s | output_dir=%s",
        context.sample.sample_id,
        context.manual_dir,
    )
    try:
        context.manual_dir.mkdir(parents=True, exist_ok=True)
        load_case = context.load_case or _load_load_case(context.fea_ready_dir / "load_case.json")
        context.load_case = load_case
        instructions_path = write_freecad_instructions(
            sample_id=context.sample.sample_id,
            step_path=context.fea_ready_dir / "fea_ready.step",
            load_case=load_case,
            output_path=context.manual_dir / "freecad_instructions.md",
            force=context.config.force,
        )
        report_path = context.manual_dir / "fea_report.json"
        write_manual_fea_report_template(
            sample_id=context.sample.sample_id,
            output_path=report_path,
            force=context.config.force,
        )
        artifact_paths = {
            "freecad_instructions_path": str(instructions_path),
            "fea_report_template_path": str(report_path),
        }
        context.artifact_paths.update(artifact_paths)
        logger.info(
            "build_manual_fea_stage | done | sample_id=%s | instructions_path=%s",
            context.sample.sample_id,
            instructions_path,
        )
        return artifact_paths
    except Exception:
        logger.exception(
            "build_manual_fea_stage | failed | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.manual_dir,
        )
        raise


def build_post_fea_stage(context: PipelineContext) -> dict[str, Any]:
    """Gate State C on manual FEA evidence and generate the post-FEA revision."""

    logger.info(
        "build_post_fea_stage | start | sample_id=%s | output_dir=%s",
        context.sample.sample_id,
        context.post_fea_dir,
    )
    try:
        context.post_fea_dir.mkdir(parents=True, exist_ok=True)
        load_case = context.load_case or _load_load_case(context.fea_ready_dir / "load_case.json")
        context.load_case = load_case
        manual_report_path = context.manual_dir / "fea_report.json"
        screenshot_paths = required_manual_fea_evidence_paths(context.manual_dir)
        try:
            validation = validate_post_fea_inputs(manual_report_path, screenshot_paths)
        except FileNotFoundError as exc:
            logger.info(
                "build_post_fea_stage | blocked | sample_id=%s | reason=%s",
                context.sample.sample_id,
                exc,
            )
            return {
                "stage_status": "blocked",
                "manual_report_path": str(manual_report_path),
                "expected_screenshot_dir": str(context.manual_dir / "screenshots"),
                "notes": [str(exc)],
            }

        if not validation["is_complete"]:
            notes = [
                f"missing_fields={validation['missing_fields']}",
                f"missing_evidence_paths={validation['missing_evidence_paths']}",
            ]
            logger.info(
                "build_post_fea_stage | blocked | sample_id=%s | notes=%s",
                context.sample.sample_id,
                notes,
            )
            return {
                "stage_status": "blocked",
                "manual_report_path": validation["manual_report_path"],
                "expected_screenshot_dir": str(context.manual_dir / "screenshots"),
                "notes": notes,
            }

        fea_revision_code_path = context.fea_ready_dir / "fea_revision_code.py"
        fea_revision_code = _read_text(fea_revision_code_path)
        fea_report = validation["report"]
        revision_result = revise_code_after_fea(
            fea_revision_code=fea_revision_code,
            load_case=load_case,
            fea_report=fea_report,
            screenshots=screenshot_paths,
            config=context.config,
        )
        execute_result = execute_and_export_post_fea_revision_cadquery(
            _read_text(revision_result.code_path),
            output_dir=context.post_fea_dir,
            force=context.config.force,
        )
        views_dir = context.post_fea_dir / "views"
        rendered_views = render_views(Path(execute_result["stl_path"]), views_dir, force=context.config.force)
        final_result = replace(
            revision_result,
            step_path=Path(execute_result["step_path"]),
            stl_path=Path(execute_result["stl_path"]),
            execution_log_path=context.post_fea_dir / "execution_log.txt",
            view_paths={name: Path(path) for name, path in rendered_views.items()},
        )
        artifact_paths = {
            "post_fea_prompt_path": str(final_result.prompt_path),
            "post_fea_code_path": str(final_result.code_path),
            "post_fea_change_log_path": str(final_result.change_log_path),
            "post_fea_provenance_path": str(final_result.provenance_path),
            "post_fea_step_path": str(final_result.step_path),
            "post_fea_stl_path": str(final_result.stl_path),
            "post_fea_execution_log_path": str(final_result.execution_log_path),
            "post_fea_view_front_path": str(final_result.view_paths["front"]),
            "post_fea_view_side_path": str(final_result.view_paths["side"]),
            "post_fea_view_top_path": str(final_result.view_paths["top"]),
            "post_fea_view_iso_path": str(final_result.view_paths["iso"]),
            "post_fea_view_grid_path": str(final_result.view_paths["grid"]),
            "post_fea_load_case_path": str(final_result.load_case_path),
            "post_fea_manual_report_path": str(final_result.manual_report_path),
        }
        context.artifact_paths.update(artifact_paths)
        logger.info(
            "build_post_fea_stage | done | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.post_fea_dir,
        )
        return {"stage_status": "passed", **artifact_paths}
    except Exception:
        logger.exception(
            "build_post_fea_stage | failed | sample_id=%s | output_dir=%s",
            context.sample.sample_id,
            context.post_fea_dir,
        )
        raise


def run_full_pipeline(config: PipelineConfig, selection: dict) -> PipelineSummary:
    """Run the full one-sample CAD-to-FEA pipeline."""

    logger.info(
        "run_full_pipeline | start | config_name=%s | selection_keys=%s",
        config.config_name,
        sorted(selection.keys()),
    )
    context: PipelineContext | None = None
    try:
        context = prepare_run_context(config, selection)
        initialize_run_manifest(
            context.manifest_path,
            context.sample.sample_id,
            context.config.config_name,
            context.sample_output_dir,
        )
        _record_stage(context, STAGE_RESOLVE_CONFIG, "passed")
        _record_stage(context, STAGE_INSPECT_SCHEMA, "skipped")
        _record_stage(context, STAGE_LOAD_SAMPLE, "passed")
        _record_stage(context, STAGE_SAVE_ORIGINAL_PROMPT, "passed", write_original_prompt_stage(context))
        _record_stage(context, STAGE_GENERATE_ORIGINAL, "passed", generate_original_code_stage(context))
        _record_stage(context, STAGE_EXECUTE_ORIGINAL, "passed", execute_original_stage(context))
        _record_stage(context, STAGE_RENDER_ORIGINAL, "passed", render_original_stage(context))
        _record_stage(context, STAGE_BUILD_FEA_READY, "passed", build_fea_ready_prompt_stage(context))
        _record_stage(context, STAGE_GENERATE_FEA_READY, "passed", generate_fea_ready_code_stage(context))
        _record_stage(context, STAGE_EXECUTE_FEA_READY, "passed", execute_fea_ready_stage(context))
        _record_stage(context, STAGE_RENDER_FEA_READY, "passed", render_fea_ready_stage(context))
        _record_stage(context, STAGE_BUILD_COMPARISON, "passed", build_comparison_stage(context))
        _record_stage(context, STAGE_BUILD_MANUAL_FEA, "passed", build_manual_fea_stage(context))
        post_fea_result = build_post_fea_stage(context)
        post_fea_notes = post_fea_result.pop("notes", None)
        post_fea_status = str(post_fea_result.pop("stage_status", "passed"))
        _record_stage(context, STAGE_BUILD_POST_FEA, post_fea_status, post_fea_result, notes=post_fea_notes)
        finalize_run_manifest(context.manifest_path)
        context.artifact_paths["run_manifest_path"] = str(context.manifest_path)
        _record_stage(context, STAGE_WRITE_MANIFEST, "passed", {"run_manifest_path": str(context.manifest_path)})
        summary = _build_summary(context)
        logger.info(
            "run_full_pipeline | done | sample_id=%s | output_dir=%s",
            summary.sample_id,
            summary.output_dir,
        )
        return summary
    except Exception as exc:
        if context is not None:
            _record_failure(context, _infer_failed_stage(context), exc)
            try:
                finalize_run_manifest(context.manifest_path)
            except Exception:
                logger.exception(
                    "run_full_pipeline | failed to finalize manifest | sample_id=%s | manifest_path=%s",
                    context.sample.sample_id,
                    context.manifest_path,
                )
        logger.exception(
            "run_full_pipeline | failed | config_name=%s",
            config.config_name,
        )
        raise


def _record_stage(
    context: PipelineContext,
    stage_name: str,
    status: str,
    artifact_paths: Mapping[str, Any] | None = None,
    notes: list[str] | None = None,
) -> None:
    """Update the in-memory and on-disk manifest for one stage."""

    context.stage_statuses[stage_name] = status
    if artifact_paths:
        context.artifact_paths.update({key: str(value) for key, value in dict(artifact_paths).items()})
    update_run_manifest(
        context.manifest_path,
        stage_name=stage_name,
        status=status,
        artifact_paths={key: str(value) for key, value in dict(artifact_paths or {}).items()},
        notes=notes,
    )


def _record_failure(context: PipelineContext, stage_name: str, error: BaseException) -> None:
    """Capture a readable failure entry for the manifest and summary."""

    failure = {
        "stage_name": stage_name,
        "error_type": type(error).__name__,
        "message": str(error),
    }
    context.stage_statuses[stage_name] = "failed"
    context.failures.append(failure)
    append_run_failure(context.manifest_path, stage_name=stage_name, message=str(error))
    update_run_manifest(context.manifest_path, stage_name=stage_name, status="failed")


def _infer_failed_stage(context: PipelineContext) -> str:
    """Return the most recently started stage when a failure bubbles up."""

    ordered_stages = [
        STAGE_WRITE_MANIFEST,
        STAGE_BUILD_POST_FEA,
        STAGE_BUILD_MANUAL_FEA,
        STAGE_BUILD_COMPARISON,
        STAGE_RENDER_FEA_READY,
        STAGE_EXECUTE_FEA_READY,
        STAGE_GENERATE_FEA_READY,
        STAGE_BUILD_FEA_READY,
        STAGE_RENDER_ORIGINAL,
        STAGE_EXECUTE_ORIGINAL,
        STAGE_GENERATE_ORIGINAL,
        STAGE_SAVE_ORIGINAL_PROMPT,
        STAGE_LOAD_SAMPLE,
        STAGE_INSPECT_SCHEMA,
        STAGE_RESOLVE_CONFIG,
    ]
    for stage_name in ordered_stages:
        if context.stage_statuses.get(stage_name) == "running":
            return stage_name
    for stage_name in ordered_stages:
        if stage_name not in context.stage_statuses:
            return stage_name
    return STAGE_RESOLVE_CONFIG


def _build_summary(context: PipelineContext) -> PipelineSummary:
    """Build a PipelineSummary from the final manifest state."""

    write_run_manifest(context.manifest_path, _current_manifest_payload(context))
    return PipelineSummary(
        sample_id=context.sample.sample_id,
        output_dir=context.sample_output_dir,
        stage_statuses=dict(context.stage_statuses),
        artifact_paths=dict(context.artifact_paths),
        failures=list(context.failures),
    )


def _current_manifest_payload(context: PipelineContext) -> dict[str, Any]:
    """Create the manifest payload from the in-memory context."""

    return {
        "sample_id": context.sample.sample_id,
        "config_name": context.config.config_name,
        "output_dir": str(context.sample_output_dir),
        "started_at": _manifest_started_at(context.manifest_path),
        "finished_at": _manifest_finished_at(context.manifest_path),
        "stage_statuses": dict(context.stage_statuses),
        "artifact_paths": dict(context.artifact_paths),
        "failures": list(context.failures),
    }


def _manifest_started_at(manifest_path: Path) -> str:
    """Preserve the original manifest start timestamp if it exists."""

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return str(manifest.get("started_at") or "")
    except Exception:
        return ""


def _manifest_finished_at(manifest_path: Path) -> str | None:
    """Read the final manifest timestamp if it exists."""

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        finished_at = manifest.get("finished_at")
        return str(finished_at) if finished_at is not None else None
    except Exception:
        return None


def _normalize_selection(selection: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize run selection flags into a dispatchable payload."""

    normalized = {
        "sample_id": selection.get("sample_id"),
        "random": bool(selection.get("random", False)),
        "expert_random": bool(selection.get("expert_random", False)),
    }
    selection_count = sum(
        [
            bool(normalized["sample_id"] and str(normalized["sample_id"]).strip()),
            normalized["random"],
            normalized["expert_random"],
        ]
    )
    if selection_count != 1:
        raise ValueError("Provide exactly one of sample_id, random, or expert_random.")
    if normalized["sample_id"] is not None:
        normalized["sample_id"] = str(normalized["sample_id"]).strip()
    return normalized


def _resolve_connection_string(runtime_config: Mapping[str, Any]) -> str:
    """Extract the DB connection string from a loaded YAML config."""

    connection_string = _nested_string(runtime_config, ("db", "connection_string"))
    if not connection_string:
        connection_string = _nested_string(runtime_config, ("connection_string",))
    if not connection_string:
        raise ValueError("DB connection string is required. Set CAD_DB_CONNECTION_STRING or db.connection_string.")
    if "${" in connection_string:
        raise ValueError("DB connection string is unresolved. Set CAD_DB_CONNECTION_STRING before running.")
    return connection_string


def _nested_string(config: Mapping[str, Any], path: tuple[str, ...]) -> str:
    """Return a stripped string at a nested mapping path."""

    current: Any = config
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return ""
        current = current[key]
    if not isinstance(current, str):
        return ""
    return current.strip()


def _ensure_original_prompt(context: PipelineContext) -> str:
    """Return the original prompt text from memory or disk."""

    if context.original_prompt:
        return context.original_prompt
    prompt_path = context.original_dir / "original_prompt.txt"
    if prompt_path.exists():
        context.original_prompt = _read_text(prompt_path)
        return context.original_prompt
    context.original_prompt = context.sample.prompt
    return context.original_prompt


def _ensure_original_code(context: PipelineContext) -> str:
    """Return the original DB CadQuery code from memory or disk."""

    if context.original_code:
        return context.original_code
    code_path = context.original_dir / "database_original_code.py"
    if code_path.exists():
        context.original_code = _read_text(code_path)
        return context.original_code
    if context.sample.ground_truth_code:
        context.original_code = context.sample.ground_truth_code
        return context.original_code
    raise FileNotFoundError(f"Original DB code not found: {code_path}")


def _ensure_fea_prompt(context: PipelineContext) -> str:
    """Return the State B revision prompt text from memory or disk."""

    if context.fea_ready_prompt:
        return context.fea_ready_prompt
    for filename in ("fea_revision_prompt.txt", "fea_ready_prompt.txt"):
        prompt_path = context.fea_ready_dir / filename
        if prompt_path.exists():
            context.fea_ready_prompt = _read_text(prompt_path)
            return context.fea_ready_prompt
    if context.load_case is None:
        context.load_case = _load_load_case(context.fea_ready_dir / "load_case.json")
    if context.selector_hints is None:
        context.selector_hints = _load_selector_hints(context.fea_ready_dir / "selector_hints.json")
    context.fea_ready_prompt = build_fea_prompt(
        _ensure_original_prompt(context),
        _ensure_original_code(context),
        context.load_case,
        context.selector_hints,
    )
    return context.fea_ready_prompt


def _build_state_b_load_case(sample_id: str) -> LoadCase:
    """Build the canonical State B load case defaults."""

    return LoadCase(
        sample_id=sample_id,
        units="mm",
        material={
            "name": "Aluminum 6061-T6",
            "youngs_modulus_pa": 68_900_000_000,
            "poissons_ratio": 0.33,
            "yield_strength_pa": 276_000_000,
        },
        boundary_conditions=[
            {
                "id": "fixed_region",
                "type": "fixed_displacement",
                "description": "wall-facing mounting plate face",
                "selector": None,
            }
        ],
        loads=[
            {
                "id": "load_region",
                "type": "force",
                "magnitude_n": 200,
                "direction": [0, 0, -1],
                "description": "top face near free end",
                "selector": None,
            }
        ],
        requirements={
            "max_displacement_mm": 1.0,
            "required_safety_factor": 2.0,
            "max_von_mises_pa": 138_000_000,
        },
    )


def _build_state_b_selector_hints(sample_id: str) -> SelectorHints:
    """Build the canonical State B selector hints defaults."""

    return SelectorHints(
        sample_id=sample_id,
        fixed_region_description="wall-facing mounting plate face",
        load_region_description="top face near free end",
        fixed_region_selector={"axis": "x", "side": "minimum"},
        load_region_selector={"axis": "x", "side": "maximum"},
        notes=[
            "Confirm the fixed region before running FreeCAD FEM.",
            "Confirm the load region before running FreeCAD FEM.",
        ],
    )


def _load_selector_hints(selector_hints_path: Path) -> SelectorHints:
    """Load selector hints JSON into the dataclass form."""

    if not selector_hints_path.exists():
        raise FileNotFoundError(f"Selector hints file not found: {selector_hints_path}")
    raw = json.loads(selector_hints_path.read_text(encoding="utf-8"))
    return SelectorHints(
        sample_id=str(raw["sample_id"]),
        fixed_region_description=str(raw["fixed_region_description"]),
        load_region_description=str(raw["load_region_description"]),
        fixed_region_selector=dict(raw["fixed_region_selector"]),
        load_region_selector=dict(raw["load_region_selector"]),
        notes=list(raw.get("notes", [])),
    )


def _load_load_case(load_case_path: Path) -> LoadCase:
    """Load a load case JSON file into the dataclass form."""

    if not load_case_path.exists():
        raise FileNotFoundError(f"Load case file not found: {load_case_path}")
    raw = json.loads(load_case_path.read_text(encoding="utf-8"))
    return LoadCase(
        sample_id=str(raw["sample_id"]),
        units=str(raw["units"]),
        material=dict(raw["material"]),
        boundary_conditions=list(raw["boundary_conditions"]),
        loads=list(raw["loads"]),
        requirements=dict(raw["requirements"]),
    )


def _require_code(code: str, code_path: Path) -> str:
    """Return code text or load it from the expected artifact path."""

    if code:
        return code
    if not code_path.exists():
        raise FileNotFoundError(f"CadQuery code not found: {code_path}")
    return _read_text(code_path)


def _write_text_artifact(output_path: Path, text: str, *, force: bool) -> None:
    """Write a text artifact without overwriting unless force is enabled."""

    if output_path.exists() and not force:
        raise FileExistsError(f"Existing artifact found at {output_path}. Use force=True to overwrite.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text((text or "").rstrip() + "\n", encoding="utf-8")


def _read_text(path: Path) -> str:
    """Read a UTF-8 text file and return its contents."""

    return Path(path).read_text(encoding="utf-8")
