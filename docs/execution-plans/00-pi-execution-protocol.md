# Pi Execution Protocol: One-Sample CADCodeVerify to FEA-Ready CAD

## Purpose

This document tells Pi how to execute the CAD-Physics implementation safely across multiple sessions. Pi must treat this protocol as the operating rules for the full feature.

## Source Of Truth

Read these files before implementation:

1. `docs/ai_context/DOC_TAXONOMY.md` — documentation authority and update rules.
2. `conversations/01-start.md` — main research intent.
3. `docs/gpt-specs/01-basic-sample-fea.md` — original feature guide.
4. `docs/execution-plans/01-basic-sample-fea-confirmed-spec.md` — confirmed local contract.
5. `docs/execution-plans/02-basic-sample-fea-architecture.md` — technical structure and layer decisions.
6. `docs/execution-plans/03-basic-sample-fea-pi-microtasks.md` — executable task list.
7. `docs/execution-plans/04-basic-sample-fea-checkpoints.md` — checkpoint gates.
8. `docs/execution-plans/06-pi-sequential-execution-prompt.md` — reusable task-loop prompt for Pi.
9. `docs/session_state.md` — current progress and resume state.

If these documents disagree, stop and update the execution-plan document that is wrong before writing code.

## Main Intent

The feature is a first implementation step toward physics-aware CAD generation. Pi must build a one-sample workflow that connects CADCodeVerify-style prompt/code generation to FEA-ready engineering artifacts:

- expert prompt or selected DB sample,
- generated baseline CadQuery model,
- STEP-first geometry handoff,
- structured `load_case.json`,
- FEA-ready prompt and generated FEA-ready CadQuery model,
- manual FreeCAD FEM + CalculiX instructions,
- manual FEA report template,
- post-FEA feedback prompt.

Do not turn this task into a full benchmark, automated solver integration, training loop, or generic CAD rendering tool.

## Small-Model Operating Mode

Pi must assume the implementation may be executed by a smaller model with limited context retention. Follow these rules:

1. Read only the minimum required context for the current task:
   - `docs/ai_context/DOC_TAXONOMY.md`
   - `00-pi-execution-protocol.md`
   - current phase section in `03-basic-sample-fea-pi-microtasks.md`
   - matching contract section in `01-basic-sample-fea-confirmed-spec.md`
   - matching structure section in `02-basic-sample-fea-architecture.md`
   - current `docs/session_state.md`
2. Do not implement more than one task before running that task's verify command.
3. Do not rename planned files, functions, CLI commands, or artifact names unless the execution docs are updated first.
4. From Phase 2 onward, use `code_base/fea_cad_one_sample/` as the working root. Paths written as `src/...`, `tests/...`, `notebooks/...`, or `outputs/...` are relative to that module root.
5. Before editing, restate the exact files for the current task in `docs/session_state.md`.
6. After each task, record:
   - files created or modified,
   - verify command run,
   - PASS or FAIL,
   - exact next task.
7. If a task is missing an exact file path, function name, output artifact, or verify command, stop and repair the execution docs before coding.

## No-Guess Rule

Pi must not invent:

- alternate file names,
- alternate directory names,
- alternate CLI flags,
- alternate artifact names,
- alternate public function names,
- extra phases not present in the microtask file.

If Pi believes a change would improve the design, Pi must first update the spec, architecture, tasks, checkpoints, and session state before implementing that change.

## Required Skill Order

Pi must use these skills in this order:

1. `discover-codebase`
   - Run before touching files.
   - Inspect CAD-Physics and the referenced CAD Design source paths.
   - Confirm no existing local module owns the requested behavior.

2. `write-spec`
   - Keep `01-basic-sample-fea-confirmed-spec.md` aligned with the implementation.
   - If the feature behavior changes, update the spec first.

3. `write-plan`
   - Use `02-basic-sample-fea-architecture.md`.
   - Do not implement if the architecture document is incomplete.

4. `decompose-tasks`
   - Use `03-basic-sample-fea-pi-microtasks.md`.
   - Execute one task at a time.

5. `create-module`
   - Required before creating `code_base/fea_cad_one_sample/`.

6. `design-layered-module`
   - Required before creating `src/` structure.
   - Enforce public interface, runner, orchestration, core, schema, and utility layers.

7. `design-python-code`
   - Required before adding schemas/classes or grouped core functions.
   - Prefer dataclasses for data contracts and functions for stateless transforms.

8. `design-runner`
   - Required before writing `src/main.py`, `src/runners.py`, or `src/orchestration/pipeline.py`.
   - Runner/orchestration files must call stage functions only.

9. `add-observability`
   - Required for every production Python file.
   - Add `logger = logging.getLogger(__name__)`.
   - Log start, done, and failure for public and core functions.

10. `write-tests`
    - Required in the same phase as each public function.
    - Tests import from public entry points only.

11. `verify-checkpoint`
    - Required at the end of each phase.
    - Do not begin the next phase unless the checkpoint passes.

12. `write-module-readme`
    - Required after creating or changing `code_base/fea_cad_one_sample/README.md`.
    - README must include a Mermaid layer diagram.

13. `update-codebase-map` and `update-system-diagram`
    - Required after module creation, public API changes, or pipeline flow changes.

14. `update-docs`
    - Required before final completion.

15. `design-feature-notebook`
    - Required if creating `notebooks/one_sample_fea_inspection.ipynb`.
    - The notebook must import from public entry points only.

16. `handoff-coding-agent`
    - Required after every checkpoint if stopping.
    - Required whenever context may be lost or a task is incomplete.

Use `refactor-module` and `deprecate-code` only if Pi restructures or retires already-created files. They are not part of the happy path.

## Tracking Rules

Pi must update these files during execution:

- `docs/execution-plans/03-basic-sample-fea-pi-microtasks.md`
  - Mark a task `[x]` only after its verify command passes.
  - Mark a checkpoint `[x]` only after every item in the checkpoint passes.

- `docs/session_state.md`
  - Update after every phase.
  - Update before stopping, even if no phase is complete.
  - Include the exact next task text.

- `code_base/fea_cad_one_sample/outputs/sample_<sample_id>/run_manifest.json`
  - Record sample ID, config, stage statuses, artifact paths, and failures.

- `execution_log.txt`
  - Write one per CAD execution stage.
  - Capture stdout, stderr, exit status, and exported files.

- `README.md`, `docs/ai_context/CODEBASE_MAP.md`, and `docs/ai_context/SYSTEM_WORKFLOW_MAP.md`
  - Update before final completion.

- `docs/ai_context/DOC_TAXONOMY.md`
  - Update if documentation authority, documentation areas, or required documentation verification rules change.

## Hard Stop Rules

Pi must stop and ask for help if any condition occurs:

- A checkpoint fails twice on the same item.
- DB schema does not expose expert prompts or an equivalent expert prompt field.
- Required environment variables are missing for the active phase.
- CadQuery cannot export STEP for a simple test box.
- Implementation would require automated FreeCAD or CalculiX execution.
- Production runtime import from CAD Design appears necessary.
- Copied CAD Design code must be modified instead of wrapped.
- A task would require changing behavior outside the one-sample prototype scope.

## CAD Design Code Policy

The feature spec says this project is standalone. Pi may inspect CAD Design code freely and may temporarily import CAD Design code in one-off investigation commands. Production code must copy the needed code into `src/copied_from_cadcodeverify/` and adapt through local wrappers.

If Pi believes a production runtime import from CAD Design is safer than copying, stop and ask the user. If the user approves runtime imports, update `01-basic-sample-fea-confirmed-spec.md`, `02-basic-sample-fea-architecture.md`, and `docs/ai_context/CODEBASE_MAP.md` before implementing that change.

## Completion Rule

The feature is not complete until:

- Every phase checkpoint in `04-basic-sample-fea-checkpoints.md` passes.
- `03-basic-sample-fea-pi-microtasks.md` has all required tasks checked.
- `docs/session_state.md` says final checkpoint passed.
- The final acceptance command creates a complete `outputs/sample_<sample_id>/` workspace.
