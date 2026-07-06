# Remediation Microtasks: Correct A/B/C CAD-Physics Experiment

## Status

Draft task plan. Do not execute until the user approves this remediation package.

## Execution Rules

- Execute phases in order.
- Do not mark a task complete until its verify command passes.
- Every phase ends with a verify-checkpoint task.
- If the same verify item fails twice, stop, update `docs/session_state.md`, and ask for help.
- Preserve existing dirty notebook and output changes unless the user explicitly asks to remove them.
- Do not automate FreeCAD or CalculiX.
- Do not implement more than the current task before verification.

## Phase 1: Docs, Session State, And Authority Alignment

**Goal:** make the documentation system reflect the corrected experiment before code changes.

### Task 1.1 - Create missing execution log if absent

**Layer:** Documentation  
**Files:** `docs/ai_context/AGENT_EXECUTION_LOG.md`  
**What to build:** If the file is absent, create it from the governance template and add an entry explaining the remediation start.  
**Verify:**

```bash
test -s docs/ai_context/AGENT_EXECUTION_LOG.md
```

### Task 1.2 - Update authority docs to recognize remediation package

**Layer:** Documentation  
**Files:** `docs/ai_context/DOC_TAXONOMY.md`, `docs/session_state.md`  
**What to build:** Record `docs/remediation/` as the current approved remediation planning package and note that it supersedes conflicting baseline-generation language.  
**Verify:**

```bash
rg -n "docs/remediation|State A|database_original_code|post_fea_revision" docs/ai_context/DOC_TAXONOMY.md docs/session_state.md
```

### Task 1.3 - Verify-checkpoint

**Layer:** Checkpoint  
**What to build:** Run Phase 1 checkpoint from `05-remediation-checkpoints.md`.  
**Verify:** all Phase 1 checkpoint items pass.

## Phase 2: DB Original-Code Loading And State A

**Goal:** State A is the unchanged DB original prompt and DB original CAD code.

### Task 2.1 - Preserve DB original code in sample schema

**Layer:** Schema/Core  
**Files:** `src/schemas/sample.py`, `src/db/load_sample.py`, `tests/test_db_loading.py`, `tests/test_schemas.py`  
**What to build:** Populate `CADSample.ground_truth_code` from the DB code column and fail sample loading if a selected State A sample lacks original CAD code.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_db_loading.py tests/test_schemas.py -q
```

### Task 2.2 - Replace baseline generation with DB-original persistence

**Layer:** Core  
**Files:** `src/cad/generate_original.py` or replacement `src/cad/dataset_original.py`, `tests/test_generate_original.py`  
**What to build:** Persist `database_original_code.py`, `original_prompt.txt`, `metadata.json`, `provenance.json`, and a SHA-256 code hash without calling the LLM.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_generate_original.py -q
```

### Task 2.3 - Execute and render State A from DB code

**Layer:** Core/Orchestration  
**Files:** `src/orchestration/pipeline.py`, `src/runners.py`, `src/interfaces.py`, `tests/test_pipeline.py`, `tests/test_interfaces.py`  
**What to build:** Route State A execution/export/render through `01_dataset_original/` and prove STEP/STL/views are written from DB code.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_pipeline.py tests/test_interfaces.py -q
```

### Task 2.4 - Verify-checkpoint

**Layer:** Checkpoint  
**What to build:** Run Phase 2 checkpoint from `05-remediation-checkpoints.md`.  
**Verify:** DB code hash preservation and no State A LLM-call checks pass.

## Phase 3: State B FEA-Constrained Revision

**Goal:** State B revises State A using FEA constraints.

### Task 3.1 - Add revision schemas and selector hints

**Layer:** Schema  
**Files:** `src/schemas/fea.py`, `src/schemas/pipeline.py`, `tests/test_schemas.py`, `tests/test_load_case.py`  
**What to build:** Add `SelectorHints`, `FEARevisionResult`, and `RevisionChangeLog` dataclasses; write `selector_hints.json`.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_schemas.py tests/test_load_case.py -q
```

### Task 3.2 - Build State B revision prompt

**Layer:** Core  
**Files:** `src/prompts/build_fea_prompt.py`, `src/prompts/prompt_templates.py`, `tests/test_fea_prompt.py`  
**What to build:** Prompt must include original prompt, original code, load case, selector hints, preserve-identity rules, permitted modification list, and change-log schema instructions.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_fea_prompt.py -q
```

### Task 3.3 - Implement `revise_code_for_fea(...)`

**Layer:** Core/Public Interface  
**Files:** `src/cad/generate_fea_ready.py`, `src/interfaces.py`, `tests/test_generate_fea_ready.py`, `tests/test_interfaces.py`  
**What to build:** Replace independent prompt generation with a revision function that receives State A prompt/code and writes `fea_revision_code.py`, `fea_revision_change_log.json`, and `provenance.json`.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_generate_fea_ready.py tests/test_interfaces.py -q
```

### Task 3.4 - Execute and render State B

**Layer:** Orchestration/Core  
**Files:** `src/orchestration/pipeline.py`, `src/visualization/render_views.py`, `tests/test_pipeline.py`, `tests/test_rendering.py`  
**What to build:** Write `02_fea_constrained_revision/fea_revision.step`, STL, execution log, four views, `grid.png`, and `annotated_support_load.png`.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_pipeline.py tests/test_rendering.py -q
```

### Task 3.5 - Verify-checkpoint

**Layer:** Checkpoint  
**What to build:** Run Phase 3 checkpoint from `05-remediation-checkpoints.md`.  
**Verify:** State B revision prompt/API/change-log checks pass.

## Phase 4: A/B/C Visualization And Geometry Metrics

**Goal:** produce strong visualizations and deterministic comparisons.

### Task 4.1 - Add deterministic geometry metrics

**Layer:** Core  
**Files:** `src/visualization/geometry_metrics.py`, `tests/test_geometry_metrics.py`  
**What to build:** Compute bounding box, volume, surface area, center of mass, connected component count where available, watertightness where available, and pairwise deltas.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_geometry_metrics.py -q
```

### Task 4.2 - Add three-state visual comparison

**Layer:** Core  
**Files:** `src/visualization/compare_views.py`, `src/reports/build_comparison_report.py`, `tests/test_rendering.py`, `tests/test_reports.py`  
**What to build:** Generate `state_abc_grid.png`, `geometry_metrics.json`, `geometry_metrics.md`, `prompt_and_code_diffs.md`, `change_log_summary.md`, and `final_experiment_report.md`.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_rendering.py tests/test_reports.py -q
```

### Task 4.3 - Verify-checkpoint

**Layer:** Checkpoint  
**What to build:** Run Phase 4 checkpoint from `05-remediation-checkpoints.md`.  
**Verify:** A/B/C comparison artifact checks pass with fixture geometries.

## Phase 5: Manual FEA Gate And Real State C Revision

**Goal:** State C generates real CAD only after actual manual FEA evidence exists.

### Task 5.1 - Validate manual FEA completion

**Layer:** Core  
**Files:** `src/fea/manual_report.py`, `src/fea/post_fea_prompt.py`, `tests/test_manual_fea_report.py`  
**What to build:** Add validation that required values are non-null and required screenshots/result files exist.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_manual_fea_report.py -q
```

### Task 5.2 - Implement `revise_code_after_fea(...)`

**Layer:** Core/Public Interface  
**Files:** `src/fea/post_fea_prompt.py`, `src/cad/post_fea_revision.py`, `src/interfaces.py`, `tests/test_post_fea_revision.py`, `tests/test_interfaces.py`  
**What to build:** Generate `post_fea_prompt.txt`, call model only after gate passes, parse `post_fea_code.py`, write `post_fea_change_log.json` and `provenance.json`.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_post_fea_revision.py tests/test_interfaces.py -q
```

### Task 5.3 - Execute/render State C and update pipeline manifest

**Layer:** Orchestration/Core  
**Files:** `src/orchestration/pipeline.py`, `src/orchestration/manifest.py`, `tests/test_pipeline.py`, `tests/test_run_manifest.py`  
**What to build:** Write `05_post_fea_revision/post_fea.step`, STL, execution log, views, and blocked manifest state when manual FEA evidence is incomplete.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_pipeline.py tests/test_run_manifest.py -q
```

### Task 5.4 - Verify-checkpoint

**Layer:** Checkpoint  
**What to build:** Run Phase 5 checkpoint from `05-remediation-checkpoints.md`.  
**Verify:** State C blocked and completed paths are both tested.

## Phase 6: Real Multi-Notebook Experiment Walkthrough

**Goal:** replace synthetic-box proof with real experiment notebooks.

### Task 6.1 - Split notebook walkthrough

**Layer:** Notebook  
**Files:** `notebooks/00_select_real_sample.ipynb` through `notebooks/05_final_abc_comparison.ipynb`  
**What to build:** Add notebooks that inspect real sample selection, State A, State B, manual FEA handoff, State C, and final comparison.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
python - <<'PY'
from pathlib import Path
for path in sorted(Path("notebooks").glob("*.ipynb")):
    text = path.read_text(encoding="utf-8")
    if "sample_box" in text:
        raise SystemExit(f"synthetic sample_box reference found in {path}")
print("notebook synthetic-box scan passed")
PY
```

### Task 6.2 - Add notebook contract tests

**Layer:** Tests/Notebook  
**Files:** `tests/test_notebook_contracts.py`  
**What to build:** Assert notebooks import only public surfaces, keep outputs cleared, do not hardcode credentials, and reference real `sample_<sample_id>` artifacts.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q
```

### Task 6.3 - Verify-checkpoint

**Layer:** Checkpoint  
**What to build:** Run Phase 6 checkpoint from `05-remediation-checkpoints.md`.  
**Verify:** notebook contract and synthetic-box rejection checks pass.

## Phase 7: CLI, Manifest, README, Maps, And Compatibility Cleanup

**Goal:** align all public surfaces and docs with the corrected experiment.

### Task 7.1 - Update CLI commands and compatibility behavior

**Layer:** Public Interface  
**Files:** `src/main.py`, `src/runners.py`, `tests/test_cli.py`  
**What to build:** Add explicit State A/B/C and A/B/C comparison commands while preserving or clearly documenting old command compatibility.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_cli.py -q
```

### Task 7.2 - Remove old CAD Design runtime import fallback

**Layer:** Utilities/Core  
**Files:** `src/copied_from_cadcodeverify/db/connections.py`, local wrapper files, tests for connector construction  
**What to build:** Ensure production runtime uses local copied LLM code and does not resolve old CAD Design paths.  
**Verify:**

```bash
cd code_base/fea_cad_one_sample
rg -n "ensure_code_base_on_path|from utils\\.llm|from code_base\\.utils" src
```

Expected: no production runtime fallback remains, except source comments if explicitly documented.

### Task 7.3 - Update docs and diagrams

**Layer:** Documentation  
**Files:** `README.md`, `docs/ai_context/CODEBASE_MAP.md`, `docs/ai_context/SYSTEM_WORKFLOW_MAP.md`, `docs/session_state.md`, `docs/execution-plans/*` or approved replacements  
**What to build:** Align docs with State A/B/C folders, APIs, manifest, notebooks, and checkpoints.  
**Verify:**

```bash
rg -n "01_dataset_original|02_fea_constrained_revision|05_post_fea_revision|revise_code_for_fea|revise_code_after_fea" README.md ../../docs/ai_context ../../docs/session_state.md
```

### Task 7.4 - Final verify-checkpoint

**Layer:** Checkpoint  
**What to build:** Run final checkpoint from `05-remediation-checkpoints.md`.  
**Verify:** full unit suite, compileall, docs scan, and real/smoke artifact checks pass.

