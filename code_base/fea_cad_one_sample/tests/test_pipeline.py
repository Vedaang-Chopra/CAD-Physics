"""Unit tests for the full pipeline orchestration."""

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.interfaces import PipelineConfig, run_full_pipeline


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
        original_dir=sample_output_dir / "01_original",
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
    monkeypatch.setattr("src.orchestration.pipeline.generate_original_code_stage", lambda ctx: {"original_code_path": str(ctx.original_dir / "original_code.py")})
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
