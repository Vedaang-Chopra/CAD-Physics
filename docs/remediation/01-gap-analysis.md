# Remediation Gap Analysis: CADCodeVerify DB Original to FEA Revision Experiment

## Purpose

This document records the mismatch between the original CAD-Physics experiment intent and the current `fea_cad_one_sample` implementation. It is the first file in a user-directed remediation package under `docs/remediation/`.

The requested remediation package is planning-only. It does not implement Python code, rewrite notebooks, or modify generated outputs.

## Rulebook And Project Context Inspected

The remediation plan is grounded in these local sources:

- `~/agent-governance/AGENTS.md`
- `~/agent-governance/skills/core/discover-codebase.md`
- `~/agent-governance/skills/core/write-spec.md`
- `~/agent-governance/skills/core/write-plan.md`
- `~/agent-governance/skills/core/decompose-tasks.md`
- `~/agent-governance/skills/core/verify-checkpoint.md`
- `~/agent-governance/skills/core/design-feature-notebook.md`
- `~/agent-governance/skills/core/update-codebase-map.md`
- `~/agent-governance/skills/core/update-system-diagram.md`
- `~/agent-governance/skills/core/update-docs.md`
- `~/agent-governance/skills/core/handoff-coding-agent.md`
- `docs/ai_context/DOC_TAXONOMY.md`
- `docs/ai_context/CODEBASE_MAP.md`
- `docs/ai_context/SYSTEM_WORKFLOW_MAP.md`
- `docs/session_state.md`
- `docs/gpt-specs/01-basic-sample-fea.md`
- `docs/execution-plans/00-pi-execution-protocol.md`
- `docs/execution-plans/01-basic-sample-fea-confirmed-spec.md`
- `docs/execution-plans/02-basic-sample-fea-architecture.md`
- `docs/execution-plans/03-basic-sample-fea-pi-microtasks.md`
- `docs/execution-plans/04-basic-sample-fea-checkpoints.md`
- `docs/execution-plans/05-basic-sample-fea-handoff-template.md`
- `docs/execution-plans/06-pi-sequential-execution-prompt.md`
- `conversations/01-start.md`
- current `code_base/fea_cad_one_sample/` implementation, tests, notebook, and untracked outputs

Important governance note: `docs/ai_context/AGENT_EXECUTION_LOG.md` is required by the global rulebook but is currently missing. The remediation execution plan must either create it from the governance template before coding or record that absence as a blocker before implementation proceeds.

Path note: the governance default uses `docs/specs/`, `docs/plans/`, and `docs/tasks/`. The user explicitly requested this remediation planning package under `docs/remediation/`, so these files are intentionally placed here.

## Current Dirty Worktree Context

Before remediation planning, the worktree already contained:

- modified `code_base/fea_cad_one_sample/notebooks/one_sample_fea_inspection.ipynb`
- untracked `code_base/fea_cad_one_sample/outputs/`

Future coding agents must preserve those existing changes unless the user explicitly asks to reset or remove them.

## Core Experiment Drift

The original experiment was supposed to answer:

> What geometry changes happen because physical constraints and actual FEA feedback were introduced?

That requires three related states:

```text
State A: original CADCodeVerify DB prompt + original DB CAD code
State B: State A revised with FEA constraints
State C: State B revised with actual manual FEA results
```

The current implementation does not yet run that experiment. It generates a new State A from the prompt, generates State B as an independent prompt-to-code result, and stops State C at prompt/report scaffolding.

## Evidence Table

| Area | Original intent | Current implementation | Corrected contract |
|---|---|---|---|
| State A source | Load original prompt and original CadQuery code from the DB | `src/db/load_sample.py` queries `g.python_code AS ground_truth_code` but stores it only in `metadata` and returns `CADSample(..., ground_truth_code=None)` | `CADSample.ground_truth_code` must contain DB code; State A saves it unchanged as `database_original_code.py` |
| State A code path | Execute the DB original code unchanged | `src/cad/generate_original.py::generate_original_code()` builds an LLM connector and generates `original_code.py` from `sample.prompt` | No LLM call in State A; persist prompt/code/provenance/hash, then execute/export the DB code |
| State B relationship to A | Revise the original code with FEA constraints | `src/cad/generate_fea_ready.py::generate_fea_ready_code(fea_ready_prompt, config)` only receives a prompt | Replace with `revise_code_for_fea(original_prompt, original_code, load_case, selector_hints, config)` |
| State B artifacts | Revision code plus change log, provenance, selector hints, annotated support/load view | Current artifacts are `fea_ready_prompt.txt`, `load_case.json`, `fea_ready_code.py`, STEP/STL, simple views | Add `selector_hints.json`, `fea_revision_change_log.json`, `provenance.json`, `annotated_support_load.png`, and revision naming |
| State C behavior | Generate post-FEA revised CAD from actual manual FreeCAD FEM + CalculiX results | `src/fea/post_fea_prompt.py::write_post_fea_prompt()` writes `fea_feedback_prompt.txt` and `comparison_after_fea.md` only | Add gated `revise_code_after_fea(...)` that writes real code, STEP/STL, views, provenance, and change log |
| Manual FEA gate | User fills real result values before post-FEA CAD revision | `fea_report.json` template can have null values and still feeds prompt/report scaffolding | State C must refuse pending/null required values and missing result screenshots |
| Visualization | Compare original, FEA-constrained, and post-FEA geometry visually and numerically | `src/visualization/compare_views.py` supports two columns only; `render_views.py` emits four basic views | Add A/B/C grid, per-state `grid.png`, annotated support/load view, and deterministic geometry metrics |
| Notebook proof | Real DB sample walkthrough of experiment artifacts | notebook executes a synthetic CadQuery box named `sample_box` and outputs temp artifacts | Replace with real multi-notebook walkthrough over `outputs/sample_<sample_id>/` |
| Checkpoints | Real experiment artifacts prove completion | `docs/execution-plans/04-basic-sample-fea-checkpoints.md` accepts unit utility checks and post-FEA prompt/template artifacts | Checkpoints must require DB-original preservation, no State A LLM call, State B revision evidence, real State C CAD, and real notebook walkthrough |
| Standalone policy | No production runtime imports from CAD Design | `src/copied_from_cadcodeverify/db/connections.py` falls back to importing `utils.llm.llm` via old path resolution | Local wrappers must use copied local code; old CAD Design path resolution in runtime is a bug |

## Current Implementation Hotspots

- `code_base/fea_cad_one_sample/src/db/load_sample.py`
  - SQL fetches `ground_truth_code`.
  - `_frame_to_sample()` drops it from the dataclass field and stores it in metadata.

- `code_base/fea_cad_one_sample/src/cad/generate_original.py`
  - Generates the baseline using an LLM.
  - Writes `original_raw_response.txt`, which should not exist for DB-original State A.

- `code_base/fea_cad_one_sample/src/cad/generate_fea_ready.py`
  - Treats the FEA-ready design as an independent prompt generation.
  - Does not receive or explicitly preserve the original CAD code.

- `code_base/fea_cad_one_sample/src/fea/post_fea_prompt.py`
  - Creates feedback text and markdown comparison scaffolding.
  - Does not call a model, execute CAD, export geometry, or render post-FEA views.

- `code_base/fea_cad_one_sample/src/orchestration/pipeline.py`
  - Stage names and output folders encode the drift: `generate_original_code`, `02_fea_ready`, `05_post_fea_refinement`.
  - The full pipeline completes before a real post-FEA CAD model exists.

- `code_base/fea_cad_one_sample/notebooks/one_sample_fea_inspection.ipynb`
  - Uses a hardcoded local DB connection string.
  - Executes a synthetic `cq.Workplane('XY').box(20, 10, 5)` and writes `sample_box.step` / `sample_box.stl`.

- `docs/execution-plans/01-basic-sample-fea-confirmed-spec.md`
  - Explicitly says to generate baseline `original_code.py` from the expert prompt and treat ground-truth code as optional reference.
  - This contradicts the original `docs/gpt-specs/01-basic-sample-fea.md`, which says to extract and execute original DB code.

## Remediation Direction

The remediation must convert the project from a two-generation demo into a controlled related-state experiment:

1. State A is the unchanged DB original.
2. State B is a physics-constrained revision of State A.
3. State C is a post-FEA revision of State B after real manual solver evidence.
4. Final artifacts make A/B/C geometry differences inspectable through images, metrics, code diffs, prompts, change logs, and notebooks.

