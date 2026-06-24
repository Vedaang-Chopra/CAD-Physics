# Confirmed Spec: One-Sample CADCodeVerify to FEA-Ready CAD

**Status:** Confirmed for implementation planning  
**Source feature guide:** `docs/gpt-specs/01-basic-sample-fea.md`  
**Execution owner:** Pi coding agent  

## Purpose

Build a standalone one-sample prototype that converts an expert CAD prompt into a baseline CadQuery model, transforms the prompt into an FEA-ready engineering prompt, generates an FEA-ready CadQuery model, exports STEP/STL files, renders comparison views, and prepares manual FreeCAD FEM + CalculiX validation artifacts.

This implements the first practical step from `conversations/01-start.md`: move CADCodeVerify from geometry-only CAD toward physics-aware CAD by adding a structured load case, engineering handoff artifacts, and post-FEA feedback scaffolding.

## Confirmed Decisions

- Use CadQuery Python as the primary CAD representation.
- Use STEP as the primary engineering geometry handoff format.
- Use STL only for visualization or mesh preview.
- Use expert prompts as the source input.
- Generate the baseline `original_code.py` from the selected expert prompt.
- Use ground-truth code only as optional reference and mapping metadata.
- Create a dedicated `cad_physics` conda environment by cloning the existing `cadquery` environment.
- Copy all three allowed configs into this project:
  - `config_gpt_5_4_mini.yaml`
  - `config_gptoss_openrotuer.yaml`
  - `config_qwen_coder.yaml`
- Default generation config is `config_gpt_5_4_mini.yaml`.
- Keep FreeCAD FEM + CalculiX manual in this prototype.
- Do not build a benchmark, training loop, or automated FEA solver integration.

## Scope

In scope:

- Load one DB sample by explicit sample ID, random sample, or expert-random sample.
- Inspect DB schema before assuming column names.
- Prefer expert prompts and FEA-sensible shapes for random selection.
- Generate baseline CadQuery code from the selected expert prompt.
- Execute baseline and FEA-ready CadQuery code.
- Export baseline and FEA-ready STEP/STL files.
- Render baseline and FEA-ready standard views.
- Build `fea_ready_prompt.txt`.
- Build `load_case.json`.
- Build side-by-side comparison artifacts.
- Build manual FreeCAD FEM instructions.
- Build `fea_report.json` template.
- Build post-FEA feedback prompt template.
- Track stage statuses and artifact paths in `run_manifest.json`.

Out of scope:

- Fully automated FreeCAD.
- Fully automated CalculiX.
- Multi-sample benchmark construction.
- Training, fine-tuning, or model evaluation at scale.
- Automatic physical correctness guarantees.
- Complex thermal, fluid, buckling, fatigue, or nonlinear simulation.
- Runtime dependency on CAD Design unless the user explicitly approves a spec change.

## Required Output Layout

The full pipeline writes under:

```text
code_base/fea_cad_one_sample/outputs/sample_<sample_id>/
```

Required subdirectories:

```text
01_original/
02_fea_ready/
03_comparison/
04_manual_freecad_fea/
05_post_fea_refinement/
```

Required artifacts:

```text
01_original/original_prompt.txt
01_original/original_code.py
01_original/metadata.json
01_original/original.step
01_original/original.stl
01_original/execution_log.txt
01_original/views/front.png
01_original/views/side.png
01_original/views/top.png
01_original/views/iso.png

02_fea_ready/fea_ready_prompt.txt
02_fea_ready/load_case.json
02_fea_ready/fea_ready_code.py
02_fea_ready/fea_ready.step
02_fea_ready/fea_ready.stl
02_fea_ready/execution_log.txt
02_fea_ready/views/front.png
02_fea_ready/views/side.png
02_fea_ready/views/top.png
02_fea_ready/views/iso.png

03_comparison/side_by_side.png
03_comparison/prompt_diff.md
03_comparison/geometry_diff_notes.md

04_manual_freecad_fea/freecad_instructions.md
04_manual_freecad_fea/fea_report.json

05_post_fea_refinement/fea_feedback_prompt.txt
05_post_fea_refinement/comparison_after_fea.md

run_manifest.json
```

## FEA Defaults

Use these exact default values:

```json
{
  "material": "Aluminum 6061-T6",
  "youngs_modulus_pa": 68900000000,
  "poissons_ratio": 0.33,
  "yield_strength_pa": 276000000,
  "load_n": 200,
  "load_direction": [0, 0, -1],
  "max_displacement_mm": 1.0,
  "required_safety_factor": 2.0,
  "max_von_mises_pa": 138000000
}
```

Compute:

```text
max_von_mises_pa = yield_strength_pa / required_safety_factor
```

## CLI Contract

Pi must implement these commands:

```bash
python -m src.main inspect-schema --config config_gpt_5_4_mini.yaml
python -m src.main run --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
python -m src.main run --random --config config_gpt_5_4_mini.yaml
python -m src.main run --expert-random --config config_gpt_5_4_mini.yaml
python -m src.main render-only --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
python -m src.main build-fea-prompt --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
python -m src.main build-freecad-instructions --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
python -m src.main compare --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
```

All runtime examples must use:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python
```

Relevant write commands must also accept `--force`.

Without `--force`, existing output artifacts must not be overwritten.

Selection rules:

- `run` requires exactly one of `--sample-id`, `--random`, or `--expert-random`.
- `render-only`, `build-fea-prompt`, `build-freecad-instructions`, and `compare` require `--sample-id`.
- `inspect-schema` does not accept sample-selection flags.
- If conflicting sample-selection flags are passed, CLI must exit non-zero with a clear error.

## Run Manifest Contract

`run_manifest.json` must be machine-readable JSON with these top-level keys:

```json
{
  "sample_id": "string",
  "config_name": "string",
  "output_dir": "string",
  "started_at": "ISO-8601 string",
  "finished_at": "ISO-8601 string or null",
  "stage_statuses": {},
  "artifact_paths": {},
  "failures": []
}
```

Each stage record must capture:

- stage name,
- status, using one of `pending`, `running`, `passed`, `failed`, or `skipped`,
- artifact paths written by that stage,
- short notes or failure text when relevant.

## Acceptance Criteria

The implementation is complete when this command creates a full sample workspace:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m src.main run --expert-random --config config_gpt_5_4_mini.yaml
```

The user can then:

1. Open `02_fea_ready/fea_ready.step` in FreeCAD.
2. Assign Aluminum 6061-T6.
3. Apply fixed support to the fixed/support face.
4. Apply a 200 N downward force to the load face.
5. Mesh with Gmsh or Netgen.
6. Run CalculiX manually.
7. Save screenshots and fill `04_manual_freecad_fea/fea_report.json`.
8. Generate or inspect `05_post_fea_refinement/fea_feedback_prompt.txt`.

## Required Error Handling

Every failure must write a readable log and preserve previous outputs:

- DB connection missing.
- DB schema missing expected prompt/code fields.
- DB sample missing expert prompt.
- Model generation fails.
- Model response cannot be parsed into CadQuery code.
- CadQuery execution fails.
- CadQuery result object cannot be found.
- STEP export fails.
- STL export fails.
- Rendering fails.
- Manual FEA result is not available yet.

## Spec Change Rule

If Pi needs to change any behavior in this document, Pi must:

1. Stop implementation.
2. Update this spec.
3. Update `02-basic-sample-fea-architecture.md`.
4. Update affected tasks and checkpoints.
5. Record the decision in `docs/session_state.md`.

## Documentation Execution Rule

Pi must follow `docs/ai_context/DOC_TAXONOMY.md` while implementing this spec. Documentation updates are part of implementation completion, not a final cleanup step.

Required documentation behavior:

- Keep this confirmed spec aligned with implemented behavior.
- Keep `CODEBASE_MAP.md` aligned with module structure and public APIs.
- Keep `SYSTEM_WORKFLOW_MAP.md` aligned with pipeline stages.
- Keep the module README aligned with CLI commands, artifacts, and public entry points.
- Keep `docs/session_state.md` updated after each phase, checkpoint, and stop.
