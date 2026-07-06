# DOC_TAXONOMY.md

> Documentation authority map for CAD-Physics. Pi must use this before editing or relying on project docs.

## Purpose

This project exists to build a first practical CADCodeVerify-to-FEA workflow: generate or adapt one CadQuery CAD sample, make it FEA-ready, export STEP-first geometry, prepare a manual FreeCAD FEM + CalculiX validation path, and capture feedback artifacts for later physics-aware refinement.

The current approved remediation package lives under `docs/remediation/` and temporarily supersedes conflicting baseline-generation wording in lower-authority docs for this controlled A/B/C experiment.

The documentation system must keep that intent visible. Docs must not drift into a generic CAD generation project, a full benchmark, or an automated FEA solver integration.

## Documentation Authority Order

When documents disagree, use this order:

1. `conversations/01-start.md`
   - Main research intent and conceptual framing.
   - Explains why physics verification matters and why geometry-only CAD is insufficient.
2. `docs/gpt-specs/01-basic-sample-fea.md`
   - Original feature guide.
   - Defines the one-sample prototype and output expectations.
3. `docs/execution-plans/01-basic-sample-fea-confirmed-spec.md`
   - Confirmed implementation contract.
   - Pi must keep this aligned with what is actually built.
4. `docs/execution-plans/02-basic-sample-fea-architecture.md`
   - Technical file/layer ownership.
5. `docs/execution-plans/03-basic-sample-fea-pi-microtasks.md`
   - Executable task list.
6. `docs/execution-plans/04-basic-sample-fea-checkpoints.md`
   - Phase gates and final acceptance.
7. `docs/ai_context/CODEBASE_MAP.md`
   - Current module ownership and public API map.
8. `docs/ai_context/SYSTEM_WORKFLOW_MAP.md`
   - Pipeline and workflow diagram.
9. `docs/session_state.md`
   - Current execution state and resume point.

For the current remediation, `docs/remediation/` is the approved execution package and must be treated as the active source of truth when it conflicts with older baseline-generation wording.

If lower-authority docs disagree with higher-authority docs, Pi must update the lower-authority docs before implementation continues.

## Documentation Areas

| Area | Purpose | Owner Rule |
|---|---|---|
| `conversations/` | User/advisor intent and background discussion | Read-only reference during implementation |
| `docs/gpt-specs/` | Original feature specs | Do not edit unless user asks to revise original spec |
| `docs/execution-plans/` | Pi execution contract, architecture, tasks, checkpoints, and prompts | Update whenever execution behavior changes |
| `docs/remediation/` | Approved remediation package for the current controlled A/B/C experiment | Keep aligned with the active corrected experiment and phase gates |
| `docs/ai_context/` | Agent-facing maps and documentation taxonomy | Update whenever structure, workflow, or doc authority changes |
| `docs/ai_context/AGENT_EXECUTION_LOG.md` | Cross-session task log | Update after every task attempt and before starting the next task |
| `docs/session_state.md` | Active progress tracker | Update after every phase, every checkpoint, and before stopping |
| `code_base/fea_cad_one_sample/README.md` | Module-facing human and agent guide | Create/update with module implementation |
| `code_base/fea_cad_one_sample/notebooks/00_select_real_sample.ipynb` through `05_final_abc_comparison.ipynb` plus `one_sample_fea_inspection.ipynb` | Public notebook walkthrough and overview | Keep public-only imports and real `outputs/sample_<sample_id>/` artifacts |
| `code_base/fea_cad_one_sample/notebooks/fea_replication/` | Deterministic STEP→mesh→CalculiX notebook series | Keep public-only imports and explicit `outputs/fea_replication/baseline/` artifacts |

## Required Documentation Updates During Implementation

Pi must update docs in the same task that changes behavior:

- New module or directory: update `CODEBASE_MAP.md`.
- New or changed pipeline stage: update `SYSTEM_WORKFLOW_MAP.md`.
- New or changed public API: update `CODEBASE_MAP.md`, module README, and `interfaces.py` exports.
- New or changed schema/config: update confirmed spec and `CODEBASE_MAP.md`.
- New or changed CLI command/flag: update confirmed spec, architecture, module README, and checkpoints.
- Changed artifact layout: update confirmed spec, checkpoints, module README, and session state.
- Divergence from original plan: update confirmed spec, architecture, microtasks, checkpoints, and session state before coding.

## Documentation Verification Rules

Before final completion, Pi must verify:

```bash
test -s docs/ai_context/DOC_TAXONOMY.md
test -s docs/ai_context/CODEBASE_MAP.md
test -s docs/ai_context/SYSTEM_WORKFLOW_MAP.md
test -s docs/session_state.md
rg -n "fea_cad_one_sample|run_full_pipeline|FreeCAD|CalculiX|run_manifest" docs/ai_context docs/execution-plans docs/session_state.md
```

Pi must also run the unresolved marker scan from `03-basic-sample-fea-pi-microtasks.md`.

## Main Intent Guardrails

Pi must preserve these project constraints:

- This is a one-sample prototype, not a benchmark.
- STEP is the primary engineering handoff.
- STL is secondary for visualization or mesh preview.
- FreeCAD FEM + CalculiX are manual in this version.
- `load_case.json`, `fea_report.json`, and `fea_feedback_prompt.txt` are required because they connect CAD generation to physical verification.
- Ground-truth CAD code is reference-only unless the confirmed spec is changed.
- CAD Design code may be copied and wrapped locally; production runtime imports from CAD Design are not allowed without user approval.

## Changelog

| Date | Change |
|---|---|
| 2026-06-24 | Created documentation taxonomy and authority rules for CAD-Physics execution. |
| 2026-06-24 | Added inspection-notebook ownership guidance and current module-doc alignment rules. |
