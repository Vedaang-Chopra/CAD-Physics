# Checkpoints: One-Sample CADCodeVerify to FEA-Ready CAD

## Checkpoint Rules

- Pi must run every item in a checkpoint.
- Pi must record actual command output in `docs/session_state.md`.
- Pi must not proceed to the next phase until the current checkpoint passes.
- If the same checkpoint item fails twice, Pi must stop and ask for help.

## Phase Checkpoint Table

| Phase | Checkpoint | Required Result |
|---|---|---|
| 0 | Runtime env imports | `cad_physics` imports CadQuery, OpenAI, render, DB, and pytest libraries |
| 1 | Planning docs | Execution docs, sequential execution prompt, session state, documentation taxonomy, and AI context docs exist with no unresolved markers |
| 2 | Module skeleton | Directory structure exists and `compileall` passes |
| 3 | Schemas/config | Schema and config tests pass; three config YAMLs copied |
| 4 | Copied code | Copied code compiles and every copied file has source-path comments |
| 5 | DB loader | DB loader tests pass and `inspect-schema` works with DB env set |
| 6 | Baseline CAD | Original-generation tests pass, simple CadQuery box exports STEP/STL, and overwrite guards work |
| 7 | FEA prompt/load case | Prompt/load-case tests pass and max von Mises is `138000000` |
| 8 | FEA-ready CAD | FEA-ready generation tests pass and failure logs are non-destructive |
| 9 | Rendering/comparison | Rendering and report tests pass |
| 10 | FreeCAD/manual FEA | Manual instruction/report tests pass |
| 11 | CLI/pipeline | CLI, interfaces, and run-manifest tests pass; `--help` works; full run works when env vars are set |
| 12 | Notebook/docs | Notebook exists; README and AI maps reflect actual code |

## Required Commands

Environment:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python - <<'PY'
import cadquery, openai, trimesh, pandas, sqlalchemy, psycopg2, pytest
print("cad_physics ready")
PY
```

Compile:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m compileall code_base/fea_cad_one_sample
```

Tests:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests -q
```

CLI help:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m src.main --help
```

Schema inspection:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m src.main inspect-schema --config config_gpt_5_4_mini.yaml
```

Full run:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m src.main run --expert-random --config config_gpt_5_4_mini.yaml
```

Documentation verification:

```bash
test -s docs/ai_context/DOC_TAXONOMY.md
test -s docs/ai_context/CODEBASE_MAP.md
test -s docs/ai_context/SYSTEM_WORKFLOW_MAP.md
test -s docs/session_state.md
rg -n "fea_cad_one_sample|run_full_pipeline|FreeCAD|CalculiX|run_manifest" docs/ai_context docs/execution-plans docs/session_state.md
```

## Final Artifact Checklist

The final run must create:

```text
outputs/sample_<sample_id>/run_manifest.json

outputs/sample_<sample_id>/01_original/original_prompt.txt
outputs/sample_<sample_id>/01_original/original_code.py
outputs/sample_<sample_id>/01_original/metadata.json
outputs/sample_<sample_id>/01_original/original.step
outputs/sample_<sample_id>/01_original/original.stl
outputs/sample_<sample_id>/01_original/execution_log.txt
outputs/sample_<sample_id>/01_original/views/front.png
outputs/sample_<sample_id>/01_original/views/side.png
outputs/sample_<sample_id>/01_original/views/top.png
outputs/sample_<sample_id>/01_original/views/iso.png

outputs/sample_<sample_id>/02_fea_ready/fea_ready_prompt.txt
outputs/sample_<sample_id>/02_fea_ready/load_case.json
outputs/sample_<sample_id>/02_fea_ready/fea_ready_code.py
outputs/sample_<sample_id>/02_fea_ready/fea_ready.step
outputs/sample_<sample_id>/02_fea_ready/fea_ready.stl
outputs/sample_<sample_id>/02_fea_ready/execution_log.txt
outputs/sample_<sample_id>/02_fea_ready/views/front.png
outputs/sample_<sample_id>/02_fea_ready/views/side.png
outputs/sample_<sample_id>/02_fea_ready/views/top.png
outputs/sample_<sample_id>/02_fea_ready/views/iso.png

outputs/sample_<sample_id>/03_comparison/side_by_side.png
outputs/sample_<sample_id>/03_comparison/prompt_diff.md
outputs/sample_<sample_id>/03_comparison/geometry_diff_notes.md

outputs/sample_<sample_id>/04_manual_freecad_fea/freecad_instructions.md
outputs/sample_<sample_id>/04_manual_freecad_fea/fea_report.json

outputs/sample_<sample_id>/05_post_fea_refinement/fea_feedback_prompt.txt
outputs/sample_<sample_id>/05_post_fea_refinement/comparison_after_fea.md
```

## Final Acceptance Checklist

- [ ] Full pipeline command exits 0.
- [ ] Baseline original STEP/STL exist.
- [ ] FEA-ready STEP/STL exist.
- [ ] Original and FEA-ready views exist.
- [ ] `load_case.json` uses Aluminum 6061-T6 defaults.
- [ ] `load_case.json` contains `max_von_mises_pa: 138000000`.
- [ ] `freecad_instructions.md` explains manual macOS FreeCAD FEM + CalculiX workflow.
- [ ] `fea_report.json` is ready for manual result entry.
- [ ] `fea_feedback_prompt.txt` can consume manual stress/displacement values.
- [ ] `run_manifest.json` records each stage status and artifact path.
- [ ] `run_manifest.json` contains top-level keys `sample_id`, `config_name`, `output_dir`, `started_at`, `finished_at`, `stage_statuses`, `artifact_paths`, and `failures`.
- [ ] Public imports from `src/interfaces.py` cover notebook and test entry points.
- [ ] Relevant write commands accept `--force`.
- [ ] CLI selection rules are enforced exactly: `run` accepts exactly one of `--sample-id`, `--random`, or `--expert-random`; stage-only commands require `--sample-id`.
- [ ] Tests pass.
- [ ] `compileall` passes.
- [ ] README, CODEBASE_MAP, SYSTEM_WORKFLOW_MAP, and session_state are updated.
- [ ] `docs/ai_context/DOC_TAXONOMY.md` exists and documentation verification commands pass.
- [ ] `docs/execution-plans/06-pi-sequential-execution-prompt.md` exists and points to the exact next-task loop.
- [ ] Docs preserve the main intent from `conversations/01-start.md`: physics-aware one-sample CAD, STEP-first handoff, manual FreeCAD/CalculiX validation, and post-FEA feedback artifacts.

## Failure Report Format

If a checkpoint fails, Pi must write this in `docs/session_state.md`:

```markdown
## Checkpoint Failure

**Phase:** <phase number and name>
**Failed command:** `<exact command>`
**Observed output:** <short exact output or path to log>
**Likely task:** <task id>
**Attempt count for this item:** <1 or 2>
**Next action:** <fix task or stop for help>
```
