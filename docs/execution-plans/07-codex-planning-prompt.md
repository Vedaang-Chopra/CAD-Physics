# Codex Planning Prompt — Notebook Series

You are in **plan mode only**. Do **not** modify code or notebooks yet.

## Read first

- `docs/ai_context/DOC_TAXONOMY.md`
- `docs/ai_context/CODEBASE_MAP.md`
- `docs/ai_context/SYSTEM_WORKFLOW_MAP.md`
- `docs/ai_context/AGENT_EXECUTION_LOG.md`
- `docs/session_state.md`
- `code_base/fea_cad_one_sample/README.md`
- every notebook under `code_base/fea_cad_one_sample/notebooks/`
- all relevant `src/` modules, especially reusable sample, prompt, mesh, solver, results, and visualization code

## Goal

Design a **simple, understandable 5-notebook series** for the one-sample FEA workflow, reusing existing Python code wherever possible.

The series should cover:

1. DB sample load + inspection + FEA prompt / LLM generation
2. input validation + physics spec
3. mesh + constraint mapping
4. CalculiX execution
5. result inspection + feedback

## Non-negotiables

- Reuse the existing Python codebase; do not duplicate logic.
- Keep notebooks thin and readable.
- Every notebook must have a mirrored Python script for testing.
- Archive old notebooks instead of scattering logic.
- Refer to visualizations and outputs explicitly.
- Stop after planning; do not implement anything.

## Deliverables

1. A technical plan markdown file.
2. A task markdown file another agent can execute directly.
3. A reuse map showing which existing modules power each notebook.
4. An archive strategy for the old notebook set.
5. Validation steps for notebook/script parity.

## What the plan must include

- Notebook-by-notebook responsibilities
- Exact file inventory
- Reused existing modules and functions
- Any new helper files needed for notebook/script parity
- Output artifacts for each notebook
- Archive/migration plan for old notebooks
- Risks, gaps, and validation commands

## Stop condition

After writing the plan and task markdown files, stop and report the paths. Do not start implementation.
