# Codex To Coding Agent Prompt: Execute CAD-Physics Remediation

Copy this entire prompt into a fresh coding-agent session after the user approves the remediation package.

---

You are implementing the CAD-Physics remediation in:

```text
/Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD-Physics
```

Your task is to fix the existing `fea_cad_one_sample` implementation so it runs the corrected controlled experiment:

```text
State A: original CADCodeVerify DB prompt + original DB CAD code
State B: State A revised with FEA constraints
State C: State B revised with actual manual FreeCAD FEM + CalculiX results
Final: compare A vs B vs C visually and numerically
```

Do not automate FreeCAD or CalculiX. First-pass FEA remains manual on macOS.

## Step 1: Read Required Rules And Docs

Before changing files, read these in order:

```text
~/agent-governance/AGENTS.md
docs/ai_context/DOC_TAXONOMY.md
docs/ai_context/CODEBASE_MAP.md
docs/ai_context/SYSTEM_WORKFLOW_MAP.md
docs/session_state.md
docs/remediation/01-gap-analysis.md
docs/remediation/02-corrected-experiment-spec.md
docs/remediation/03-remediation-architecture.md
docs/remediation/04-remediation-microtasks.md
docs/remediation/05-remediation-checkpoints.md
```

Also read:

```text
docs/gpt-specs/01-basic-sample-fea.md
docs/execution-plans/00-pi-execution-protocol.md
docs/execution-plans/01-basic-sample-fea-confirmed-spec.md
docs/execution-plans/02-basic-sample-fea-architecture.md
docs/execution-plans/03-basic-sample-fea-pi-microtasks.md
docs/execution-plans/04-basic-sample-fea-checkpoints.md
conversations/01-start.md
code_base/fea_cad_one_sample/README.md
```

If `docs/ai_context/AGENT_EXECUTION_LOG.md` is missing, create it from the governance template before coding and record that the remediation started.

## Step 2: Inspect Current Dirty State

Run:

```bash
git status --short
```

At the time the remediation package was created, these existing changes were present:

```text
 M code_base/fea_cad_one_sample/notebooks/one_sample_fea_inspection.ipynb
?? code_base/fea_cad_one_sample/outputs/
```

Preserve existing user/worktree changes unless the user explicitly asks to remove them. Do not reset, clean, or delete those artifacts.

## Step 3: Execute One Phase At A Time

Use `docs/remediation/04-remediation-microtasks.md` as the task file.

For each phase:

1. Read the full phase.
2. Read any files named by the current task.
3. Implement only the current task.
4. Run the task verify command.
5. If it fails, diagnose and fix once.
6. If the same verify item fails twice, stop.
7. Update `docs/session_state.md`.
8. Update `docs/ai_context/AGENT_EXECUTION_LOG.md`.
9. Run the phase checkpoint from `docs/remediation/05-remediation-checkpoints.md`.
10. Stop at the checkpoint and report status before starting the next phase unless the user explicitly tells you to continue.

Do not batch multiple phases.

## Step 4: Non-Negotiable Experiment Corrections

State A:

- Load original prompt from DB.
- Load original CAD code from DB.
- Save original CAD code unchanged as `database_original_code.py`.
- Execute original CAD code unchanged.
- Export STEP/STL.
- Render views.
- Record provenance and code hash.
- Do not instantiate an LLM connector.

State B:

- Receive original prompt and exact original DB code.
- Receive `load_case.json` and `selector_hints.json`.
- Revise the original design, not generate an unrelated design.
- Write `fea_revision_code.py`, `fea_revision_change_log.json`, provenance, STEP/STL, views, grid, and support/load annotation.

State C:

- Require actual manual FreeCAD FEM + CalculiX result values.
- Refuse to run when `fea_report.json` still contains null/pending values.
- Refuse to run when required screenshots/result files are missing.
- Generate real post-FEA CAD code only after the gate passes.
- Write `post_fea_code.py`, `post_fea_change_log.json`, provenance, STEP/STL, and views.

Final comparison:

- Compare A/B/C visually and numerically.
- Write `state_abc_grid.png`, `geometry_metrics.json`, `geometry_metrics.md`, code/prompt diffs, change log summary, and final experiment report.

## Step 5: Notebook Requirements

Replace the synthetic-box proof with real notebooks:

```text
notebooks/00_select_real_sample.ipynb
notebooks/01_state_a_dataset_original.ipynb
notebooks/02_state_b_fea_revision.ipynb
notebooks/03_manual_fea_handoff.ipynb
notebooks/04_state_c_post_fea_revision.ipynb
notebooks/05_final_abc_comparison.ipynb
```

Rules:

- Import only from `src.interfaces` or `src.runners`.
- No production logic in notebooks.
- No hardcoded DB credentials.
- No `sample_box` synthetic proof as final evidence.
- Keep notebooks thin, stage-based, and artifact-inspection oriented.
- Include assertions and debugging notes.

## Step 6: Standalone Runtime Rule

Production runtime imports from old CAD Design paths are bugs.

Fix any path that depends on:

```text
ensure_code_base_on_path
from utils.llm
from code_base.utils
```

Use local copied code and local wrappers instead.

## Step 7: Verification Commands

Use the project Python:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python
```

Minimum final checks:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests -q
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m compileall .
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m src.main --help
```

Run all phase-specific checks from `docs/remediation/05-remediation-checkpoints.md`.

## Step 8: Context Management

At roughly 60-70 percent context usage:

1. Finish the current task if safe.
2. Run its verify command.
3. Update `docs/session_state.md`.
4. Update `docs/ai_context/AGENT_EXECUTION_LOG.md`.
5. Stop.
6. Tell the user the exact next task from `docs/remediation/04-remediation-microtasks.md`.

Do not start a new large task near context exhaustion.

## Step 9: Completion Standard

The remediation is complete only when:

- State A is DB-original and hash-proven.
- State B is a revision of State A.
- State C is a revision of State B based on actual manual FEA values.
- The system blocks State C when manual FEA evidence is incomplete.
- A/B/C visual and numeric comparisons exist.
- Notebooks inspect real artifacts.
- Docs, maps, README, session state, and execution log are updated.
- All checkpoint commands pass.

