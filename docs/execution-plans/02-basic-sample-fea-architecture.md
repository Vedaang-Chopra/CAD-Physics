# Architecture Plan: One-Sample CADCodeVerify to FEA-Ready CAD

**Spec:** `docs/execution-plans/01-basic-sample-fea-confirmed-spec.md`  
**Status:** Ready for Pi task execution  

## Summary

Create a standalone Python package at `code_base/fea_cad_one_sample/`. The package has a thin CLI, public stage functions, a simple pipeline orchestrator, focused domain modules, dataclass schemas, copied CAD Design reference code, tests, and inspection docs.

## Runtime Environment

Pi must create and use:

```bash
conda create -n cad_physics --clone cadquery -y
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python - <<'PY'
import cadquery, openai, trimesh, pandas, sqlalchemy, psycopg2, pytest
print("cad_physics ready")
PY
```

Do not use `/opt/homebrew/bin/python3` for CadQuery execution; that interpreter is not guaranteed to have CadQuery or OpenAI installed.

## Path Convention

- Before Phase 2, paths are repo-relative.
- From Phase 2 onward, Pi must `cd code_base/fea_cad_one_sample` before running task commands unless a task explicitly needs repo-root context.
- In the microtasks file, paths written as `src/...`, `tests/...`, `notebooks/...`, and `outputs/...` are relative to `code_base/fea_cad_one_sample/`.

## Layer Assignment

| Component | Layer | File Path | Reason |
|---|---|---|---|
| CLI parser | Public entry | `code_base/fea_cad_one_sample/src/main.py` | Exposes commands only |
| Public stage API | Public entry | `code_base/fea_cad_one_sample/src/interfaces.py` | Stable imports for tests/notebook |
| Runner functions | Public runner | `code_base/fea_cad_one_sample/src/runners.py` | Thin stage wrappers |
| Full pipeline | Orchestration | `code_base/fea_cad_one_sample/src/orchestration/pipeline.py` | Calls stages in order |
| Sample loading | Core | `code_base/fea_cad_one_sample/src/db/` | DB schema inspection and selection |
| CAD execution/export | Core | `code_base/fea_cad_one_sample/src/cad/` | CadQuery execution and STEP/STL export |
| Prompt building | Core | `code_base/fea_cad_one_sample/src/prompts/` | FEA prompt text construction |
| Rendering/comparison | Core | `code_base/fea_cad_one_sample/src/visualization/` | PNG views and side-by-side image |
| FEA artifacts | Core | `code_base/fea_cad_one_sample/src/fea/` | Load case, FreeCAD instructions, manual report |
| Reports | Core | `code_base/fea_cad_one_sample/src/reports/` | Markdown comparison templates |
| Data contracts | Schemas | `code_base/fea_cad_one_sample/src/schemas/` | Dataclasses defined once |
| Copied CAD Design code | Reference utility | `code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/` | Preserved source behavior |
| Unit tests | Tests | `code_base/fea_cad_one_sample/tests/` | Public contract verification |
| Notebook | Inspection | `code_base/fea_cad_one_sample/notebooks/one_sample_fea_inspection.ipynb` | Human stage inspection |

## Required Directory Structure

```text
code_base/fea_cad_one_sample/
  README.md
  pyproject.toml
  requirements.txt
  notebooks/
    one_sample_fea_inspection.ipynb
  outputs/
  src/
    __init__.py
    interfaces.py
    runners.py
    main.py
    schemas/
      __init__.py
      sample.py
      config.py
      fea.py
      pipeline.py
    orchestration/
      __init__.py
      manifest.py
      pipeline.py
    db/
      __init__.py
      schema_inspection.py
      load_sample.py
    cad/
      __init__.py
      generate_original.py
      generate_fea_ready.py
      execute_cadquery.py
      export_geometry.py
      validate_cad_script.py
    prompts/
      __init__.py
      build_fea_prompt.py
      prompt_templates.py
    visualization/
      __init__.py
      render_views.py
      compare_views.py
    fea/
      __init__.py
      write_load_case.py
      freecad_manual_instructions.py
      manual_report.py
      post_fea_prompt.py
    reports/
      __init__.py
      build_comparison_report.py
    copied_from_cadcodeverify/
      README.md
      __init__.py
      configs/
      db/
      generation/
      llm/
      execution/
      rendering/
  tests/
```

## File Ownership Matrix

Use this as the exact ownership guide for Pi. Do not move these responsibilities into other files unless the execution docs are updated first.

| File | Owns | Does Not Own |
|---|---|---|
| `src/main.py` | CLI parsing and argument validation | pipeline business logic |
| `src/interfaces.py` | stable re-exports for tests/notebook/users | implementation logic |
| `src/runners.py` | thin runner functions for each command | domain logic, file parsing |
| `src/orchestration/pipeline.py` | stage ordering and pipeline handoff | prompt generation logic, export logic |
| `src/orchestration/manifest.py` | `run_manifest.json` creation and incremental updates | stage execution |
| `src/db/schema_inspection.py` | DB table/column inspection | sample selection policy |
| `src/db/load_sample.py` | sample selection and DB row normalization into `CADSample`, including public `load_sample(...)` dispatch | CLI handling |
| `src/cad/generate_original.py` | baseline code generation wrapper | geometry export |
| `src/cad/generate_fea_ready.py` | FEA-ready code generation wrapper | geometry export |
| `src/cad/validate_cad_script.py` | CadQuery code extraction and validation helpers shared by generation stages | LLM calls |
| `src/cad/execute_cadquery.py` | execute CadQuery Python and recover resulting solid/workplane | prompt generation |
| `src/cad/export_geometry.py` | STEP/STL export and overwrite protection | DB access |
| `src/prompts/build_fea_prompt.py` | compose FEA-ready prompt text from sample plus load case | JSON writing |
| `src/prompts/prompt_templates.py` | reusable prompt fragments/constants | file IO orchestration |
| `src/visualization/render_views.py` | standard single-model renders | markdown reports |
| `src/visualization/compare_views.py` | side-by-side visual composite | prompt text |
| `src/fea/write_load_case.py` | `LoadCase` creation and JSON serialization | prompt text |
| `src/fea/freecad_manual_instructions.py` | manual FreeCAD workflow instructions | report comparison |
| `src/fea/manual_report.py` | `fea_report.json` template writing | prompt generation |
| `src/fea/post_fea_prompt.py` | feedback prompt for post-FEA refinement | geometry export |
| `src/reports/build_comparison_report.py` | markdown comparison outputs | image rendering |

## CLI Selection Rules

Pi must implement these exact semantics:

- `run` requires exactly one of `--sample-id`, `--random`, or `--expert-random`.
- `render-only`, `build-fea-prompt`, `build-freecad-instructions`, and `compare` require `--sample-id`.
- `inspect-schema` accepts `--config` only.
- `--force` is allowed on commands that write artifacts.
- conflicting sample-selection arguments must fail before any stage work starts.

Pipeline selection payload passed into `run_full_pipeline(...)`:

```python
{
    "sample_id": str | None,
    "random": bool,
    "expert_random": bool,
}
```

## Public Interfaces

Expose these names from `src/interfaces.py`:

```python
CADSample
PipelineConfig
LoadCase
ManualFEAReport
PipelineSummary
inspect_schema
load_sample
generate_original_code
execute_and_export_cadquery
build_fea_prompt
write_load_case
generate_fea_ready_code
render_views
build_comparison_artifacts
write_freecad_instructions
write_manual_fea_report_template
write_post_fea_prompt
run_full_pipeline
```

Tests and notebooks must import from `interfaces.py` or `runners.py`, not deep `core` files.

## Pipeline Stages

`src/orchestration/pipeline.py` must call stages in this order:

1. Resolve config and output directory.
2. Inspect schema if needed.
3. Load expert prompt sample.
4. Save original prompt and metadata.
5. Generate baseline original CadQuery code.
6. Execute/export original STEP/STL.
7. Render original views.
8. Build FEA-ready prompt and load case.
9. Generate FEA-ready CadQuery code.
10. Execute/export FEA-ready STEP/STL.
11. Render FEA-ready views.
12. Build side-by-side comparison artifacts.
13. Write FreeCAD instructions and manual report template.
14. Write post-FEA refinement prompt and final comparison template.
15. Write `run_manifest.json`.
16. Print final output summary paths.

The full pipeline function must not contain business logic. It only passes outputs from one stage to the next.

## CAD Design Reference Code To Inspect

Pi must inspect these paths before deciding exactly what to copy:

```text
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/db
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/llm
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/evaluation/python_kernel.py
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/config_loader.py
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/load_data
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/generation
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/visual_analysis/rendering
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/config/config_gpt_5_4_mini.yaml
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/config/config_gptoss_openrotuer.yaml
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/config/config_qwen_coder.yaml
```

## Copied Code Rules

- Copy only the smallest needed functions/classes/files.
- Preserve copied behavior.
- Add a source-path comment at the top of every copied file.
- Do not edit copied logic to fit this project.
- Put adaptation logic in local wrappers outside `copied_from_cadcodeverify/`.
- Production runtime imports from CAD Design are not allowed unless the user approves a spec change.

## Suggested Copy Inventory

Pi should start with this minimal inventory and reduce it if inspection shows a smaller copy is sufficient:

| Need | CAD Design Source | Local Destination |
|---|---|---|
| Config loading | `utils/config_loader.py` | `copied_from_cadcodeverify/config_loader.py` |
| DB connection/schema reads | `utils/db/reader.py`, selected `load_data` helpers | `copied_from_cadcodeverify/db/` |
| LLM connector | `utils/llm/llm.py` | `copied_from_cadcodeverify/llm/llm.py` |
| Code generation/parsing | `agentic_closed_loop/modules/generation` selected parser/generator files | `copied_from_cadcodeverify/generation/` |
| Generated-code subprocess | `utils/evaluation/python_kernel.py` | `copied_from_cadcodeverify/execution/python_kernel.py` |
| Mesh rendering | `visual_analysis/rendering/renderer.py`, `pointcloud_loader.py`, `grid_export.py`, `schema.py` | `copied_from_cadcodeverify/rendering/` |
| Config YAMLs | Three allowed config files | `copied_from_cadcodeverify/configs/` |

## Schema Design

Use dataclasses.

Required data contracts:

```python
CADSample(
    sample_id: str,
    prompt: str,
    prompt_variant: str,
    source: str,
    metadata: dict,
    ground_truth_code: str | None = None,
)

PipelineConfig(
    config_name: str,
    config_path: Path,
    output_root: Path,
    force: bool = False,
    num_views: int = 4,
)

LoadCase(
    sample_id: str,
    units: str,
    material: dict,
    boundary_conditions: list[dict],
    loads: list[dict],
    requirements: dict,
)

ManualFEAReport(
    sample_id: str,
    solver: str,
    manual_run: bool,
    max_von_mises_pa: float | None,
    max_displacement_mm: float | None,
    yield_strength_pa: float,
    required_safety_factor: float,
    computed_safety_factor: float | None,
    passes_stress: bool | None,
    passes_displacement: bool | None,
    overall_pass: bool | None,
    stress_hotspot_description: str,
    notes: list[str],
)

PipelineSummary(
    sample_id: str,
    output_dir: Path,
    stage_statuses: dict,
    artifact_paths: dict,
    failures: list[dict],
)

RunManifestRecord(
    stage_name: str,
    status: str,  # one of: pending, running, passed, failed, skipped
    artifact_paths: dict,
    notes: list[str] | None = None,
)
```

`run_manifest.json` top-level keys:

```python
{
    "sample_id": str,
    "config_name": str,
    "output_dir": str,
    "started_at": str,
    "finished_at": str | None,
    "stage_statuses": dict[str, str],
    "artifact_paths": dict[str, str],
    "failures": list[dict],
}
```

## Observability Requirements

Every production module must include:

```python
import logging

logger = logging.getLogger(__name__)
```

Every public/core function logs:

- start with key input summary,
- done with key output summary,
- failure before re-raising or recording the failure.

Never log API keys, DB connection strings, full prompts, or full model responses. Full prompts/responses may be written only to explicit artifact files.

## Tests

Tests must import public interfaces only.

Minimum test files:

```text
tests/test_schemas.py
tests/test_config.py
tests/test_db_loading.py
tests/test_generate_original.py
tests/test_generate_fea_ready.py
tests/test_cad_execution.py
tests/test_fea_prompt.py
tests/test_load_case.py
tests/test_rendering.py
tests/test_reports.py
tests/test_freecad_manual.py
tests/test_manual_fea_report.py
tests/test_cli.py
tests/test_interfaces.py
tests/test_run_manifest.py
```

External services must be mocked in unit tests. DB/model calls are allowed only in explicit smoke commands and checkpoints that require environment variables.

## Documentation Updates

Before final completion, Pi must update:

- `code_base/fea_cad_one_sample/README.md`
- `docs/ai_context/CODEBASE_MAP.md`
- `docs/ai_context/SYSTEM_WORKFLOW_MAP.md`
- `docs/session_state.md`

The module README must include a Mermaid layer diagram.
