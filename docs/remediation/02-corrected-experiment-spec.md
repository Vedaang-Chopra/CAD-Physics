# Corrected Experiment Spec: DB Original to FEA Revision to Post-FEA Revision

## Status

Draft remediation spec. Do not implement code until the user approves the remediation package.

## Purpose

The corrected system must demonstrate one controlled CAD-Physics experiment:

```text
State A: original CADCodeVerify DB prompt + original DB CAD code
State B: State A revised with FEA constraints
State C: State B revised with actual manual FreeCAD FEM + CalculiX results
Final: compare A vs B vs C visually and numerically
```

The central question is:

> What geometry changes happen because physical constraints and actual FEA feedback were introduced?

## Out Of Scope

- No automated FreeCAD execution.
- No automated CalculiX execution.
- No multi-sample benchmark.
- No training, fine-tuning, or model evaluation loop.
- No production runtime dependency on the old CAD Design project.
- No use of synthetic `sample_box` artifacts as final experiment proof.
- No implementation before the remediation plan is approved.

## Required Output Layout

All experiment outputs live under:

```text
code_base/fea_cad_one_sample/outputs/sample_<sample_id>/
```

Corrected subdirectories:

```text
01_dataset_original/
02_fea_constrained_revision/
03_comparison/
04_manual_freecad_fea/
05_post_fea_revision/
run_manifest.json
```

The older folders `01_original/`, `02_fea_ready/`, and `05_post_fea_refinement/` must be migrated or retained only as backward-compatible aliases if required. The canonical corrected experiment uses the names above.

## State A: Dataset Original

State A is the untouched CADCodeVerify source sample.

Required inputs:

```text
DB expert prompt
DB original CadQuery code
DB row metadata
```

Required artifacts:

```text
01_dataset_original/
  original_prompt.txt
  database_original_code.py
  metadata.json
  provenance.json
  original.step
  original.stl
  execution_log.txt
  views/
    front.png
    side.png
    top.png
    iso.png
    grid.png
```

Requirements:

- Load expert prompt from DB.
- Load original CAD code from DB.
- Save original code unchanged as `database_original_code.py`.
- Execute the original code unchanged.
- Export STEP first.
- Export STL for visualization.
- Render standard views and a grid view.
- Record provenance and code hash.
- No LLM connector may be instantiated in State A.
- No generated `original_raw_response.txt` may be required for State A.

State A is invalid if DB code is missing, rewritten, normalized beyond line-ending preservation, or regenerated from a prompt.

## State B: FEA-Constrained Revision

State B is a revision of State A, not an unrelated design.

Required inputs:

```text
01_dataset_original/original_prompt.txt
01_dataset_original/database_original_code.py
02_fea_constrained_revision/load_case.json
02_fea_constrained_revision/selector_hints.json
```

Required artifacts:

```text
02_fea_constrained_revision/
  fea_revision_prompt.txt
  load_case.json
  selector_hints.json
  fea_revision_code.py
  fea_revision_change_log.json
  provenance.json
  fea_revision.step
  fea_revision.stl
  execution_log.txt
  views/
    front.png
    side.png
    top.png
    iso.png
    grid.png
    annotated_support_load.png
```

Requirements:

- The model receives the original prompt and the exact original DB code.
- The model is instructed to preserve original design identity.
- Permitted changes include thickness, ribs, gussets, fillets, support/load faces, meshability features, and local strengthening.
- The model must not arbitrarily redesign unrelated features.
- The model must output a machine-readable change log explaining what changed and why.
- Geometry must remain one connected solid when possible.
- Support and load regions must be visually annotatable.

Required conceptual API:

```python
def revise_code_for_fea(
    original_prompt: str,
    original_code: str,
    load_case: LoadCase,
    selector_hints: dict,
    config: PipelineConfig,
) -> FEARevisionResult:
    ...
```

This replaces the current conceptual API:

```python
generate_fea_ready_code(fea_prompt)
```

## State C: Post-FEA Revision

State C uses actual manual FreeCAD FEM + CalculiX results to revise State B.

Required inputs:

```text
02_fea_constrained_revision/fea_revision_code.py
02_fea_constrained_revision/load_case.json
04_manual_freecad_fea/fea_report.json
04_manual_freecad_fea/screenshots or result files
```

Required artifacts:

```text
05_post_fea_revision/
  post_fea_prompt.txt
  post_fea_code.py
  post_fea_change_log.json
  provenance.json
  post_fea.step
  post_fea.stl
  execution_log.txt
  views/
    front.png
    side.png
    top.png
    iso.png
    grid.png
```

Requirements:

- State C must refuse to run if required FEA result values are null or pending.
- The model receives State B code, load case, actual FEA values, hotspot notes, and screenshot/result paths.
- The model revises the existing design based on stress, displacement, safety factor, and hotspot feedback.
- If stress is too high, expected revisions include ribs, gussets, thicker sections, better load path, or fillets near hotspots.
- If displacement is too high, expected revisions include increased section height, triangular support, ribs, or stiffness improvements.
- If overbuilt, expected revisions include reducing non-critical bulk while preserving the required safety factor.
- This stage is incomplete if only `fea_feedback_prompt.txt` or `post_fea_prompt.txt` is written.

Required conceptual API:

```python
def revise_code_after_fea(
    fea_revision_code: str,
    load_case: LoadCase,
    fea_report: ManualFEAReport,
    screenshots: list[Path],
    config: PipelineConfig,
) -> PostFEARevisionResult:
    ...
```

## FEA Defaults

Use these defaults unless the selected sample requires an explicit override:

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

The load case must include support/load selector hints that can be manually confirmed in the first version:

```json
{
  "fixed_region_description": "wall-facing mounting plate face",
  "load_region_description": "top face near free end",
  "fixed_region_selector": {
    "axis": "x",
    "side": "minimum"
  },
  "load_region_selector": {
    "axis": "x",
    "side": "maximum"
  }
}
```

## Final Comparison Contract

The final comparison must include:

- A/B/C rendered image grid.
- Prompt and code diffs.
- Revision change logs.
- Deterministic geometry metrics:
  - bounding box extents
  - volume
  - surface area
  - center of mass
  - connected component count where available
  - watertightness where available
  - mesh distance or sampled surface distance where feasible
- FEA result summary.
- A written answer to: what changed because physical constraints were introduced, and what changed because actual FEA feedback was introduced?

Required artifacts:

```text
03_comparison/
  state_abc_grid.png
  prompt_and_code_diffs.md
  geometry_metrics.json
  geometry_metrics.md
  change_log_summary.md
  final_experiment_report.md
```

## Acceptance Criteria

- State A uses DB original code exactly and records a code hash.
- State A execution exports STEP/STL and standard views.
- State A proves no LLM connector was used.
- State B prompt includes original prompt, original code, load case, selector hints, and preserve-identity instructions.
- State B writes revision code, change log, provenance, STEP/STL, views, and support/load annotation.
- Manual FEA artifacts guide the user through FreeCAD FEM + CalculiX without automating the solver.
- State C refuses pending manual FEA results.
- State C writes real post-FEA code, STEP/STL, views, provenance, and change log after completed manual results.
- Final comparison contains A/B/C visual and deterministic numeric evidence.
- Notebooks walk through real sample artifacts, not synthetic box artifacts.
- Checkpoints fail if any real experiment artifact is missing.

