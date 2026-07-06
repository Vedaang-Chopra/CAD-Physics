"""Unit tests for the full pipeline orchestration."""

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from src.interfaces import PipelineConfig, run_full_pipeline
from src.orchestration.pipeline import PipelineContext, build_post_fea_stage, execute_original_stage, render_original_stage
from src.schemas.fea import LoadCase
from src.schemas.pipeline import PostFEARevisionResult
from src.schemas.sample import CADSample
from src.fea.manual_report import required_manual_fea_evidence_paths, write_manual_fea_report_template


def test_run_full_pipeline_writes_manifest_and_summary(monkeypatch, tmp_path: Path) -> None:
    """run_full_pipeline writes a manifest with stage statuses and artifact paths."""

    config_path = tmp_path / "config_gpt_5_4_mini.yaml"
    config_path.write_text("db:\n  connection_string: sqlite:///fake.db\n", encoding="utf-8")
    config = PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=config_path,
        output_root=tmp_path / "outputs",
        force=True,
    )
    sample_output_dir = config.output_root / "sample_sample-001"
    context = SimpleNamespace(
        config=config,
        selection={"sample_id": "sample-001", "random": False, "expert_random": False},
        runtime_config={"db": {"connection_string": "sqlite:///fake.db"}},
        connection_string="sqlite:///fake.db",
        sample=SimpleNamespace(sample_id="sample-001"),
        sample_output_dir=sample_output_dir,
        original_dir=sample_output_dir / "01_dataset_original",
        fea_ready_dir=sample_output_dir / "02_fea_ready",
        comparison_dir=sample_output_dir / "03_comparison",
        manual_dir=sample_output_dir / "04_manual_freecad_fea",
        post_fea_dir=sample_output_dir / "05_post_fea_refinement",
        manifest_path=sample_output_dir / "run_manifest.json",
        original_prompt="",
        fea_ready_prompt="",
        load_case=None,
        original_code="",
        fea_ready_code="",
        stage_statuses={},
        artifact_paths={},
        failures=[],
    )

    monkeypatch.setattr("src.orchestration.pipeline.prepare_run_context", lambda config, selection: context)
    monkeypatch.setattr("src.orchestration.pipeline.write_original_prompt_stage", lambda ctx: {"original_prompt_path": str(ctx.original_dir / "original_prompt.txt")})
    monkeypatch.setattr("src.orchestration.pipeline.generate_original_code_stage", lambda ctx: {"database_original_code_path": str(ctx.original_dir / "database_original_code.py"), "original_provenance_path": str(ctx.original_dir / "provenance.json")})
    monkeypatch.setattr("src.orchestration.pipeline.execute_original_stage", lambda ctx: {"original_step_path": str(ctx.original_dir / "original.step")})
    monkeypatch.setattr("src.orchestration.pipeline.render_original_stage", lambda ctx: {"original_view_front_path": str(ctx.original_dir / "views" / "front.png")})
    monkeypatch.setattr("src.orchestration.pipeline.build_fea_ready_prompt_stage", lambda ctx: {"load_case_path": str(ctx.fea_ready_dir / "load_case.json"), "fea_ready_prompt_path": str(ctx.fea_ready_dir / "fea_ready_prompt.txt")})
    monkeypatch.setattr("src.orchestration.pipeline.generate_fea_ready_code_stage", lambda ctx: {"fea_ready_code_path": str(ctx.fea_ready_dir / "fea_ready_code.py")})
    monkeypatch.setattr("src.orchestration.pipeline.execute_fea_ready_stage", lambda ctx: {"fea_ready_step_path": str(ctx.fea_ready_dir / "fea_ready.step")})
    monkeypatch.setattr("src.orchestration.pipeline.render_fea_ready_stage", lambda ctx: {"fea_ready_view_front_path": str(ctx.fea_ready_dir / "views" / "front.png")})
    monkeypatch.setattr("src.orchestration.pipeline.build_comparison_stage", lambda ctx: {"comparison_side_by_side_path": str(ctx.comparison_dir / "side_by_side.png")})
    monkeypatch.setattr("src.orchestration.pipeline.build_manual_fea_stage", lambda ctx: {"freecad_instructions_path": str(ctx.manual_dir / "freecad_instructions.md"), "fea_report_template_path": str(ctx.manual_dir / "fea_report.json")})
    monkeypatch.setattr("src.orchestration.pipeline.build_post_fea_stage", lambda ctx: {"fea_feedback_prompt_path": str(ctx.post_fea_dir / "fea_feedback_prompt.txt"), "comparison_after_fea_path": str(ctx.post_fea_dir / "comparison_after_fea.md")})

    summary = run_full_pipeline(config, {"sample_id": "sample-001", "random": False, "expert_random": False})

    assert summary.sample_id == "sample-001"
    assert summary.output_dir == sample_output_dir
    assert (sample_output_dir / "run_manifest.json").exists()
    assert summary.artifact_paths["run_manifest_path"] == str(sample_output_dir / "run_manifest.json")
    assert summary.stage_statuses["write_run_manifest"] == "passed"
    assert summary.stage_statuses["inspect_schema"] == "skipped"
    assert context.original_dir == sample_output_dir / "01_dataset_original"
    assert summary.artifact_paths["database_original_code_path"] == str(sample_output_dir / "01_dataset_original" / "database_original_code.py")


def test_original_stage_uses_database_original_code_and_dataset_directory(monkeypatch, tmp_path: Path) -> None:
    """execute_original_stage and render_original_stage use the DB-original artifacts."""

    config = PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=tmp_path / "config_gpt_5_4_mini.yaml",
        output_root=tmp_path / "outputs",
        force=True,
    )
    sample_output_dir = config.output_root / "sample_sample-001"
    context = PipelineContext(
        config=config,
        selection={"sample_id": "sample-001", "random": False, "expert_random": False},
        runtime_config={"db": {"connection_string": "sqlite:///fake.db"}},
        connection_string="sqlite:///fake.db",
        sample=CADSample(
            sample_id="sample-001",
            prompt="Design a bracket.",
            prompt_variant="expert",
            source="cadcodeverify-db",
            metadata={"selection_mode": "sample_id"},
            ground_truth_code="import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)",
        ),
        sample_output_dir=sample_output_dir,
        original_dir=sample_output_dir / "01_dataset_original",
        fea_ready_dir=sample_output_dir / "02_fea_ready",
        comparison_dir=sample_output_dir / "03_comparison",
        manual_dir=sample_output_dir / "04_manual_freecad_fea",
        post_fea_dir=sample_output_dir / "05_post_fea_refinement",
        manifest_path=sample_output_dir / "run_manifest.json",
        original_code="import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)",
    )

    called: dict[str, object] = {}

    def fake_execute_and_export_cadquery(code: str, output_dir: Path, basename: str, force: bool = False):
        called["execute"] = (code, output_dir, basename, force)
        return {"step_path": str(output_dir / f"{basename}.step"), "stl_path": str(output_dir / f"{basename}.stl")}

    def fake_render_views(stl_path: Path, views_dir: Path, force: bool = False):
        called["render"] = (stl_path, views_dir, force)
        return {"front": str(views_dir / "front.png"), "side": str(views_dir / "side.png"), "top": str(views_dir / "top.png"), "iso": str(views_dir / "iso.png")}

    monkeypatch.setattr("src.orchestration.pipeline.execute_and_export_cadquery", fake_execute_and_export_cadquery)
    monkeypatch.setattr("src.orchestration.pipeline.render_views", fake_render_views)

    execute_artifacts = execute_original_stage(context)
    render_artifacts = render_original_stage(context)

    assert called["execute"] == (
        context.original_code,
        context.original_dir,
        "original",
        True,
    )
    assert called["render"] == (
        context.original_dir / "original.stl",
        context.original_dir / "views",
        True,
    )
    assert execute_artifacts["original_step_path"] == str(context.original_dir / "original.step")
    assert execute_artifacts["original_stl_path"] == str(context.original_dir / "original.stl")
    assert render_artifacts["original_view_front_path"] == str(context.original_dir / "views" / "front.png")


def _sample_load_case() -> LoadCase:
    """Build a representative load case for State C pipeline tests."""

    return LoadCase(
        sample_id="sample-001",
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
                "description": "Wall-facing mounting plate face",
                "selector": None,
            }
        ],
        loads=[
            {
                "id": "load_region",
                "type": "force",
                "magnitude_n": 200,
                "direction": [0, 0, -1],
                "description": "Top face near free end",
                "selector": None,
            }
        ],
        requirements={
            "max_displacement_mm": 1.0,
            "required_safety_factor": 2.0,
            "max_von_mises_pa": 138_000_000,
        },
    )


def _complete_manual_report() -> dict[str, object]:
    """Build a complete manual FEA report for State C pipeline tests."""

    return {
        "sample_id": "sample-001",
        "solver": "FreeCAD FEM + CalculiX",
        "manual_run": True,
        "max_von_mises_pa": 120_000_000,
        "max_displacement_mm": 0.4,
        "yield_strength_pa": 276_000_000,
        "required_safety_factor": 2.0,
        "computed_safety_factor": 2.3,
        "passes_stress": True,
        "passes_displacement": True,
        "overall_pass": True,
        "stress_hotspot_description": "Upper fillet near the load face.",
        "notes": ["Manual run completed."],
    }


def test_build_post_fea_stage_blocks_when_manual_evidence_missing(tmp_path: Path, monkeypatch) -> None:
    """build_post_fea_stage returns a blocked status when the manual evidence is incomplete."""

    config = PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=tmp_path / "config_gpt_5_4_mini.yaml",
        output_root=tmp_path / "outputs",
        force=True,
    )
    sample_output_dir = config.output_root / "sample_sample-001"
    manual_dir = sample_output_dir / "04_manual_freecad_fea"
    fea_ready_dir = sample_output_dir / "02_fea_constrained_revision"
    manual_dir.mkdir(parents=True, exist_ok=True)
    write_manual_fea_report_template("sample-001", manual_dir / "fea_report.json")
    fea_ready_dir.mkdir(parents=True, exist_ok=True)
    (fea_ready_dir / "fea_revision_code.py").write_text("import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)\n", encoding="utf-8")

    context = PipelineContext(
        config=config,
        selection={"sample_id": "sample-001", "random": False, "expert_random": False},
        runtime_config={"db": {"connection_string": "sqlite:///fake.db"}},
        connection_string="sqlite:///fake.db",
        sample=CADSample(
            sample_id="sample-001",
            prompt="Design a bracket.",
            prompt_variant="expert",
            source="cadcodeverify-db",
            metadata={"selection_mode": "sample_id"},
            ground_truth_code="import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)",
        ),
        sample_output_dir=sample_output_dir,
        original_dir=sample_output_dir / "01_dataset_original",
        fea_ready_dir=fea_ready_dir,
        comparison_dir=sample_output_dir / "03_comparison",
        manual_dir=manual_dir,
        post_fea_dir=sample_output_dir / "05_post_fea_revision",
        manifest_path=sample_output_dir / "run_manifest.json",
        load_case=_sample_load_case(),
    )

    called = {"revise": False}

    def fake_revise(*args, **kwargs):
        called["revise"] = True
        raise AssertionError("revise_code_after_fea should not be called when evidence is missing")

    monkeypatch.setattr("src.orchestration.pipeline.revise_code_after_fea", fake_revise)

    result = build_post_fea_stage(context)

    assert result["stage_status"] == "blocked"
    assert called["revise"] is False
    assert "notes" in result
    assert not (context.post_fea_dir / "post_fea_prompt.txt").exists()


def test_build_post_fea_stage_executes_state_c_with_complete_evidence(tmp_path: Path, monkeypatch) -> None:
    """build_post_fea_stage runs State C revision and exports STEP/STL/views when evidence is complete."""

    config = PipelineConfig(
        config_name="config_gpt_5_4_mini.yaml",
        config_path=tmp_path / "config_gpt_5_4_mini.yaml",
        output_root=tmp_path / "outputs",
        force=True,
    )
    sample_output_dir = config.output_root / "sample_sample-001"
    manual_dir = sample_output_dir / "04_manual_freecad_fea"
    fea_ready_dir = sample_output_dir / "02_fea_constrained_revision"
    manual_dir.mkdir(parents=True, exist_ok=True)
    fea_ready_dir.mkdir(parents=True, exist_ok=True)
    report_path = manual_dir / "fea_report.json"
    report_path.write_text(json.dumps(_complete_manual_report(), indent=2, sort_keys=True), encoding="utf-8")
    screenshot_paths = required_manual_fea_evidence_paths(manual_dir)
    for screenshot in screenshot_paths:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        screenshot.write_text("image-bytes", encoding="utf-8")
    code_path = fea_ready_dir / "fea_revision_code.py"
    code_path.write_text("import cadquery as cq\nresult = cq.Workplane().box(3, 4, 5)\n", encoding="utf-8")

    context = PipelineContext(
        config=config,
        selection={"sample_id": "sample-001", "random": False, "expert_random": False},
        runtime_config={"db": {"connection_string": "sqlite:///fake.db"}},
        connection_string="sqlite:///fake.db",
        sample=CADSample(
            sample_id="sample-001",
            prompt="Design a bracket.",
            prompt_variant="expert",
            source="cadcodeverify-db",
            metadata={"selection_mode": "sample_id"},
            ground_truth_code="import cadquery as cq\nresult = cq.Workplane().box(1, 2, 3)",
        ),
        sample_output_dir=sample_output_dir,
        original_dir=sample_output_dir / "01_dataset_original",
        fea_ready_dir=fea_ready_dir,
        comparison_dir=sample_output_dir / "03_comparison",
        manual_dir=manual_dir,
        post_fea_dir=sample_output_dir / "05_post_fea_revision",
        manifest_path=sample_output_dir / "run_manifest.json",
        load_case=_sample_load_case(),
    )

    result_dir = context.post_fea_dir

    def fake_revise_code_after_fea(*, fea_revision_code, load_case, fea_report, screenshots, config):
        assert "box(3, 4, 5)" in fea_revision_code
        assert screenshots == screenshot_paths
        prompt_path = result_dir / "post_fea_prompt.txt"
        code_path = result_dir / "post_fea_code.py"
        change_log_path = result_dir / "post_fea_change_log.json"
        provenance_path = result_dir / "provenance.json"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text("prompt", encoding="utf-8")
        code_path.write_text("import cadquery as cq\nresult = cq.Workplane().box(4, 5, 6)\n", encoding="utf-8")
        change_log_path.write_text(json.dumps({"sample_id": "sample-001", "source_state": "State B", "target_state": "State C"}), encoding="utf-8")
        provenance_path.write_text("{}", encoding="utf-8")
        return PostFEARevisionResult(
            sample_id=load_case.sample_id,
            prompt_path=prompt_path,
            load_case_path=result_dir / "load_case.json",
            manual_report_path=report_path,
            screenshot_paths=screenshot_paths,
            code_path=code_path,
            change_log_path=change_log_path,
            provenance_path=provenance_path,
            step_path=result_dir / "post_fea.step",
            stl_path=result_dir / "post_fea.stl",
            execution_log_path=result_dir / "execution_log.txt",
            view_paths={
                "front": result_dir / "views" / "front.png",
                "side": result_dir / "views" / "side.png",
                "top": result_dir / "views" / "top.png",
                "iso": result_dir / "views" / "iso.png",
                "grid": result_dir / "views" / "grid.png",
            },
            code_hash_sha256="abc123",
        )

    def fake_execute_and_export_post_fea_revision_cadquery(code: str, output_dir: Path, force: bool = False):
        assert "box(4, 5, 6)" in code
        output_dir.mkdir(parents=True, exist_ok=True)
        step_path = output_dir / "post_fea.step"
        stl_path = output_dir / "post_fea.stl"
        step_path.write_text("step", encoding="utf-8")
        stl_path.write_text("stl", encoding="utf-8")
        return {"step_path": str(step_path), "stl_path": str(stl_path)}

    def fake_render_views(stl_path: Path, views_dir: Path, force: bool = False):
        views_dir.mkdir(parents=True, exist_ok=True)
        for name in ("front", "side", "top", "iso", "grid"):
            (views_dir / f"{name}.png").write_text(name, encoding="utf-8")
        return {name: str(views_dir / f"{name}.png") for name in ("front", "side", "top", "iso", "grid")}

    monkeypatch.setattr("src.orchestration.pipeline.revise_code_after_fea", fake_revise_code_after_fea)
    monkeypatch.setattr("src.orchestration.pipeline.execute_and_export_post_fea_revision_cadquery", fake_execute_and_export_post_fea_revision_cadquery)
    monkeypatch.setattr("src.orchestration.pipeline.render_views", fake_render_views)

    result = build_post_fea_stage(context)

    assert result["stage_status"] == "passed"
    assert result["post_fea_step_path"] == str(result_dir / "post_fea.step")
    assert result["post_fea_view_grid_path"] == str(result_dir / "views" / "grid.png")
    assert (result_dir / "post_fea_prompt.txt").exists()
    assert (result_dir / "post_fea.step").exists()
    assert (result_dir / "post_fea.stl").exists()
