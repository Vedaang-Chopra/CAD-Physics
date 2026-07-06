# Remediation Checkpoints: Artifact-Backed Experiment Gates

## Purpose

These checkpoints replace scaffold-level completion with real experiment evidence. A phase is not complete because code compiles or templates exist; it is complete only when the required State A/B/C artifacts and tests prove the corrected experiment behavior.

## Checkpoint Rules

- Run every item in a checkpoint.
- Record actual command output in `docs/session_state.md`.
- Do not proceed to the next phase until the checkpoint passes.
- If the same item fails twice, stop and ask the user for help.
- Do not count synthetic `sample_box` artifacts as experiment evidence.
- Do not count `post_fea_prompt.txt` alone as State C completion.

## Phase 1: Docs And Authority

Required checks:

```bash
test -s docs/remediation/01-gap-analysis.md
test -s docs/remediation/02-corrected-experiment-spec.md
test -s docs/remediation/03-remediation-architecture.md
test -s docs/remediation/04-remediation-microtasks.md
test -s docs/remediation/05-remediation-checkpoints.md
test -s docs/remediation/06-codex-to-coding-agent-prompt.md
test -s docs/ai_context/AGENT_EXECUTION_LOG.md
rg -n "docs/remediation|State A|State B|State C" docs/ai_context docs/session_state.md
```

Pass condition: docs exist, execution log exists, and authority docs point to the remediation package.

## Phase 2: State A Dataset Original

Required checks:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_db_loading.py tests/test_generate_original.py tests/test_pipeline.py -q
```

State A artifact checks for a smoke run or fixture run:

```bash
test -s outputs/sample_<sample_id>/01_dataset_original/original_prompt.txt
test -s outputs/sample_<sample_id>/01_dataset_original/database_original_code.py
test -s outputs/sample_<sample_id>/01_dataset_original/metadata.json
test -s outputs/sample_<sample_id>/01_dataset_original/provenance.json
test -s outputs/sample_<sample_id>/01_dataset_original/original.step
test -s outputs/sample_<sample_id>/01_dataset_original/original.stl
test -s outputs/sample_<sample_id>/01_dataset_original/execution_log.txt
test -s outputs/sample_<sample_id>/01_dataset_original/views/front.png
test -s outputs/sample_<sample_id>/01_dataset_original/views/side.png
test -s outputs/sample_<sample_id>/01_dataset_original/views/top.png
test -s outputs/sample_<sample_id>/01_dataset_original/views/iso.png
test -s outputs/sample_<sample_id>/01_dataset_original/views/grid.png
```

Required assertions:

- `database_original_code.py` byte-for-byte matches DB original code after documented newline handling.
- `provenance.json` contains a SHA-256 code hash.
- State A tests prove the LLM connector is not instantiated.
- No State A artifact depends on `original_raw_response.txt`.

## Phase 3: State B FEA-Constrained Revision

Required checks:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_fea_prompt.py tests/test_generate_fea_ready.py tests/test_load_case.py tests/test_rendering.py -q
```

State B artifact checks:

```bash
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/fea_revision_prompt.txt
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/load_case.json
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/selector_hints.json
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/fea_revision_code.py
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/fea_revision_change_log.json
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/provenance.json
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/fea_revision.step
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/fea_revision.stl
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/execution_log.txt
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/views/front.png
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/views/side.png
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/views/top.png
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/views/iso.png
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/views/grid.png
test -s outputs/sample_<sample_id>/02_fea_constrained_revision/views/annotated_support_load.png
```

Required assertions:

- State B prompt contains original prompt text.
- State B prompt contains original DB code text.
- State B prompt contains material, load, support, selector hints, and safety thresholds.
- State B prompt instructs the model to preserve original design identity.
- `fea_revision_change_log.json` is machine-readable and non-empty.

## Phase 4: Visualization And Geometry Metrics

Required checks:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_geometry_metrics.py tests/test_rendering.py tests/test_reports.py -q
```

Comparison artifact checks:

```bash
test -s outputs/sample_<sample_id>/03_comparison/state_abc_grid.png
test -s outputs/sample_<sample_id>/03_comparison/prompt_and_code_diffs.md
test -s outputs/sample_<sample_id>/03_comparison/geometry_metrics.json
test -s outputs/sample_<sample_id>/03_comparison/geometry_metrics.md
test -s outputs/sample_<sample_id>/03_comparison/change_log_summary.md
test -s outputs/sample_<sample_id>/03_comparison/final_experiment_report.md
```

Required assertions:

- Metrics include bounding box extents, volume, surface area, center of mass, and pairwise deltas.
- Metrics include connectedness/watertightness where the mesh backend supports them.
- The comparison report explicitly separates A -> B changes from B -> C changes.

## Phase 5: Manual FEA Gate And State C

Required checks:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_manual_fea_report.py tests/test_post_fea_revision.py tests/test_pipeline.py tests/test_run_manifest.py -q
```

Pending manual FEA checks:

- If `fea_report.json` contains null required values, State C exits blocked.
- If required screenshots are missing, State C exits blocked.
- Blocked State C does not call the LLM.
- `run_manifest.json` records the blocked/manual-FEA-waiting status.

Completed State C artifact checks:

```bash
test -s outputs/sample_<sample_id>/05_post_fea_revision/post_fea_prompt.txt
test -s outputs/sample_<sample_id>/05_post_fea_revision/post_fea_code.py
test -s outputs/sample_<sample_id>/05_post_fea_revision/post_fea_change_log.json
test -s outputs/sample_<sample_id>/05_post_fea_revision/provenance.json
test -s outputs/sample_<sample_id>/05_post_fea_revision/post_fea.step
test -s outputs/sample_<sample_id>/05_post_fea_revision/post_fea.stl
test -s outputs/sample_<sample_id>/05_post_fea_revision/execution_log.txt
test -s outputs/sample_<sample_id>/05_post_fea_revision/views/front.png
test -s outputs/sample_<sample_id>/05_post_fea_revision/views/side.png
test -s outputs/sample_<sample_id>/05_post_fea_revision/views/top.png
test -s outputs/sample_<sample_id>/05_post_fea_revision/views/iso.png
test -s outputs/sample_<sample_id>/05_post_fea_revision/views/grid.png
```

Required assertions:

- State C prompt contains State B code.
- State C prompt contains actual stress, displacement, safety factor, pass/fail, and hotspot text.
- `post_fea_code.py` is generated, executed, and exported.
- `post_fea_change_log.json` explains changes caused by FEA feedback.

## Phase 6: Notebook Walkthrough

Required checks:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q
python - <<'PY'
from pathlib import Path
hits = []
for path in sorted(Path("notebooks").glob("*.ipynb")):
    text = path.read_text(encoding="utf-8")
    if "sample_box" in text:
        hits.append(str(path))
if hits:
    raise SystemExit("synthetic sample_box references found: " + ", ".join(hits))
print("notebook sample_box scan passed")
PY
```

Required assertions:

- Notebooks import only public interfaces/runners.
- Notebooks do not hardcode DB credentials.
- Notebooks inspect real `outputs/sample_<sample_id>/` artifacts.
- Notebooks have stage assertions and artifact checks.
- Saved outputs and execution counts follow the project notebook contract.

## Phase 7: Final Acceptance

Required checks:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests -q
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m compileall .
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m src.main --help
```

Docs checks from repo root:

```bash
test -s docs/ai_context/DOC_TAXONOMY.md
test -s docs/ai_context/CODEBASE_MAP.md
test -s docs/ai_context/SYSTEM_WORKFLOW_MAP.md
test -s docs/session_state.md
rg -n "01_dataset_original|02_fea_constrained_revision|05_post_fea_revision|revise_code_for_fea|revise_code_after_fea" docs code_base/fea_cad_one_sample/README.md
```

Runtime import cleanup check:

```bash
cd code_base/fea_cad_one_sample
rg -n "ensure_code_base_on_path|from utils\\.llm|from code_base\\.utils" src
```

Expected: no production runtime fallback to old CAD Design imports remains.

Final artifact checklist:

- State A DB-original artifacts complete.
- State B FEA revision artifacts complete.
- Manual FreeCAD FEM + CalculiX handoff complete.
- State C blocked correctly when manual results are incomplete.
- State C complete when manual results are provided.
- A/B/C comparison artifacts complete.
- Notebook walkthroughs use real artifacts.
- `run_manifest.json` records all stages, blocked states, artifact paths, and failures.

