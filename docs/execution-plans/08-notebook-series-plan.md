# Technical Plan: Five-Notebook CAD-Physics Series

**Source prompt:** `docs/execution-plans/07-codex-planning-prompt.md`  
**Status:** Ready for executor tasking  
**Scope:** Planning only. Do not edit source code, notebooks, tests, outputs, or archives from this plan file.

## 1. Summary

This plan consolidates the current CAD-Physics notebook surface into a simple five-notebook workflow for the one-sample FEA experiment. The new series keeps notebooks thin, gives every notebook one mirrored Python script for validation, reuses the public `src.interfaces` surface, and archives superseded notebooks instead of deleting them. The five notebooks cover sample loading and State B prompt generation, input validation and physics specification, mesh and constraint mapping, CalculiX execution, and result inspection plus feedback.

## 2. Layer Assignment

| Component | Layer | File | Responsibility |
|---|---|---|---|
| Notebook series helper | Layer 2/3 - Public interface and thin orchestration | `code_base/fea_cad_one_sample/src/notebook_series.py` | Avoid by default; create only if the executor proves direct scripts would duplicate nontrivial setup or artifact checks |
| Public re-export | Layer 2 - Public interface | `code_base/fea_cad_one_sample/src/interfaces.py` | Re-export notebook-series helper functions only if `src/notebook_series.py` is justified and added |
| Sample and prompt notebook | Layer 1 - Notebook | `code_base/fea_cad_one_sample/notebooks/00_sample_prompt_generation.ipynb` | Inspect selected DB/dataset sample, persist State A, build visible State B prompt and LLM revision artifacts |
| Sample and prompt script | Layer 1 test mirror | `code_base/fea_cad_one_sample/notebooks/python_scripts/00_sample_prompt_generation.py` | Execute the same public calls and artifact checks as notebook 00 |
| Physics spec notebook | Layer 1 - Notebook | `code_base/fea_cad_one_sample/notebooks/01_input_validation_physics_spec.ipynb` | Validate generated artifacts, load case, selector hints, STEP-first inputs, and physics defaults |
| Physics spec script | Layer 1 test mirror | `code_base/fea_cad_one_sample/notebooks/python_scripts/01_input_validation_physics_spec.py` | Execute the same public calls and artifact checks as notebook 01 |
| Mesh notebook | Layer 1 - Notebook | `code_base/fea_cad_one_sample/notebooks/02_mesh_constraint_mapping.ipynb` | Prepare geometry, generate mesh, show support/load node selection, and write mesh artifacts |
| Mesh script | Layer 1 test mirror | `code_base/fea_cad_one_sample/notebooks/python_scripts/02_mesh_constraint_mapping.py` | Execute the same public calls and artifact checks as notebook 02 |
| CalculiX notebook | Layer 1 - Notebook | `code_base/fea_cad_one_sample/notebooks/03_calculix_execution.ipynb` | Run or preflight CalculiX, capture solver artifacts, and fail clearly if `ccx` is unavailable |
| CalculiX script | Layer 1 test mirror | `code_base/fea_cad_one_sample/notebooks/python_scripts/03_calculix_execution.py` | Execute the same public calls and artifact checks as notebook 03 |
| Results notebook | Layer 1 - Notebook | `code_base/fea_cad_one_sample/notebooks/04_results_feedback.ipynb` | Parse solver results, inspect manual FEA gate, build feedback/comparison artifacts, and show final evidence |
| Results script | Layer 1 test mirror | `code_base/fea_cad_one_sample/notebooks/python_scripts/04_results_feedback.py` | Execute the same public calls and artifact checks as notebook 04 |
| Notebook contract tests | Tests | `code_base/fea_cad_one_sample/tests/test_notebook_contracts.py` | Assert five-notebook inventory, cleared outputs, public imports, archive expectations, and parity references |

## 3. Notebook Responsibilities And Reuse Map

| Notebook | Story responsibility | Reused public functions and types | Required output artifacts |
|---|---|---|---|
| `00_sample_prompt_generation.ipynb` | Load one sample, inspect prompt/code, persist State A, build State B prompt, and generate/reuse State B revision code | `load_selected_sample`, `generate_original_code`, `execute_and_export_cadquery`, `render_views`, `write_load_case`, `write_selector_hints`, `build_fea_prompt`, `revise_code_for_fea`, `execute_and_export_fea_revision_cadquery` | `01_dataset_original/original_prompt.txt`, `database_original_code.py`, `original.step`, `original.stl`, `views/*.png`, `02_fea_constrained_revision/load_case.json`, `selector_hints.json`, `fea_revision_prompt.txt`, `fea_revision_code.py`, `fea_revision.step` |
| `01_input_validation_physics_spec.ipynb` | Validate State A and State B inputs, physics defaults, STEP-first handoff, load case, selector hints, and FEA replication config | `LoadCase`, `SelectorHints`, `FEAReplicationConfig`, `build_baseline_config`, `validate_manual_fea_completion` for gate visibility | `analysis_config.json` or equivalent config summary under the selected run directory, visible paths to `load_case.json`, `selector_hints.json`, `fea_revision.step` |
| `02_mesh_constraint_mapping.ipynb` | Convert the State B STEP into deterministic mesh inputs and inspect selected support/load regions | `build_baseline_config`, `prepare_geometry_artifacts`, `generate_calculix_mesh`, `GeometrySummary`, `MeshSummary`, `RegionSelectionSummary` | `geometry_summary.json`, `geometry_preview.png`, `analysis.inp`, `analysis.msh`, `mesh_summary.json`, `mesh_preview.png` |
| `03_calculix_execution.ipynb` | Run CalculiX through the existing solver helper or stop with an actionable missing-`ccx` message | `run_calculix_solver`, `run_full_replication`, `SolverRunSummary` | `analysis.stdout.txt`, `analysis.stderr.txt`, `analysis.dat`, `analysis.frd`, `analysis.sta`, `analysis.cvg`, `pipeline_summary.json` when solver runs |
| `04_results_feedback.ipynb` | Parse results, show pass/fail, inspect manual FEA gate, generate feedback prompt, and compare available states | `parse_calculix_results`, `validate_manual_fea_completion`, `build_post_fea_prompt`, `revise_code_after_fea`, `compute_geometry_metrics`, `build_state_abc_grid`, `build_final_experiment_report`, report builders | `parsed_results.json`, result table/plot, `geometry_metrics.json`, `geometry_metrics.md`, `state_abc_grid.png` when State C exists, `post_fea_prompt.txt` when manual evidence is complete |

All notebooks must import only `src.interfaces` or Python standard/third-party display libraries. Default implementation should keep setup local and small in each mirror script. Add `src/notebook_series.py` only after documenting why existing public APIs and small script-local setup are insufficient.

## 4. Interface Design Decisions

| Symbol | Form | Expression | Reason |
|---|---|---|---|
| Existing public functions listed in the reuse map | Re-export | Already exported from `src.interfaces` | The current public surface already owns the core workflow behavior |
| `run_notebook_step_00` through `run_notebook_step_04` if strictly necessary | Re-export | `from .notebook_series import run_notebook_step_00` etc. | Last resort after documenting duplicated nontrivial setup across at least three scripts |
| Shared result dataclass or dict type if strictly necessary | Re-export | `from .notebook_series import NotebookStepResult` | Last resort if parity tests require a common structured return that cannot stay script-local |

Do not wrap existing domain functions unless the wrapper is a proven notebook/script parity boundary. Do not move mesh, solver, result parsing, rendering, report logic, or simple path constants into `src/notebook_series.py`.

## 5. Error And Return Contracts

| Function | Success return | Missing/invalid input | Failure case | Raises |
|---|---|---|---|---|
| Existing public functions | Existing return contracts | Existing behavior | Existing behavior | Existing exceptions |
| Strictly necessary `run_notebook_step_XX(...)` helpers | `dict[str, Any]` with stable artifact paths, summaries, and status flags | Raise `FileNotFoundError` for missing required prior artifacts; raise `ValueError` for invalid config/sample settings | Log exception context and re-raise | `FileNotFoundError`, `ValueError`, domain exceptions from reused public functions |
| Strictly necessary shared path/config resolver | `dict[str, Path | str | bool]` or small dataclass | Raise `FileNotFoundError` when module root or config cannot be resolved | Log exception context and re-raise | `FileNotFoundError`, `ValueError` |

Notebook cells must display failures clearly but must not swallow exceptions silently. The mirrored scripts must exit non-zero on the same required-artifact failures.

## 6. Files To Create

| Path | Layer | Purpose |
|---|---|---|
| `code_base/fea_cad_one_sample/src/notebook_series.py` | Layer 2/3 | Avoid by default; create only with documented proof that direct mirror scripts would duplicate nontrivial setup or artifact checks |
| `code_base/fea_cad_one_sample/notebooks/python_scripts/00_sample_prompt_generation.py` | Layer 1 mirror | Script equivalent for notebook 00 |
| `code_base/fea_cad_one_sample/notebooks/python_scripts/01_input_validation_physics_spec.py` | Layer 1 mirror | Script equivalent for notebook 01 |
| `code_base/fea_cad_one_sample/notebooks/python_scripts/02_mesh_constraint_mapping.py` | Layer 1 mirror | Script equivalent for notebook 02 |
| `code_base/fea_cad_one_sample/notebooks/python_scripts/03_calculix_execution.py` | Layer 1 mirror | Script equivalent for notebook 03 |
| `code_base/fea_cad_one_sample/notebooks/python_scripts/04_results_feedback.py` | Layer 1 mirror | Script equivalent for notebook 04 |
| `code_base/fea_cad_one_sample/notebooks/00_sample_prompt_generation.ipynb` | Layer 1 | Thin human inspection notebook for sample, State A, and State B prompt/generation |
| `code_base/fea_cad_one_sample/notebooks/01_input_validation_physics_spec.ipynb` | Layer 1 | Thin human inspection notebook for physics spec and input validation |
| `code_base/fea_cad_one_sample/notebooks/02_mesh_constraint_mapping.ipynb` | Layer 1 | Thin human inspection notebook for mesh and region selection |
| `code_base/fea_cad_one_sample/notebooks/03_calculix_execution.ipynb` | Layer 1 | Thin human inspection notebook for solver execution/preflight |
| `code_base/fea_cad_one_sample/notebooks/04_results_feedback.ipynb` | Layer 1 | Thin human inspection notebook for result parsing, comparison, and feedback |
| `code_base/fea_cad_one_sample/notebooks/archive/2026-07/README.md` | Documentation | Archive index explaining why superseded notebooks were moved |

## 7. Files To Modify

| Path | What changes | Layer | Impact on callers |
|---|---|---|---|
| `code_base/fea_cad_one_sample/src/interfaces.py` | Prefer no change; re-export notebook-series helpers only if `src/notebook_series.py` is justified and created | Layer 2 | Preserves public-only notebook imports |
| `code_base/fea_cad_one_sample/tests/test_notebook_contracts.py` | Update inventory from old notebooks to the five target notebooks and five mirror scripts | Tests | Enforces the new notebook contract |
| `code_base/fea_cad_one_sample/README.md` | Replace old notebook list with the five-notebook series and archive note | Docs | Human docs match current workflow |
| `docs/ai_context/CODEBASE_MAP.md` | Update notebook inventory and optional `src/notebook_series.py` ownership | Docs | Agent map reflects new public surface |
| `docs/ai_context/SYSTEM_WORKFLOW_MAP.md` | Update notebook inspection flow from old series to five-step flow | Docs | Agent workflow map reflects current walkthrough |
| `docs/session_state.md` | Record notebook-series implementation status and archive location | Docs | Resume state is explicit |

Do not modify source modules for this feature unless the executor justifies `src/notebook_series.py`; if that happens, `src/interfaces.py` may change only to re-export the justified helper. Existing core behavior should be reused as-is.

## 8. Archive And Migration Plan

Move superseded notebooks into `code_base/fea_cad_one_sample/notebooks/archive/2026-07/` during implementation, preserving filenames unless a collision requires an archive index note.

Archive these top-level notebooks:

- `00_environment_and_db_check.ipynb`
- `01_select_and_load_sample.ipynb`
- `02_state_a_dataset_original.ipynb`
- `03_state_b_fea_prompt_generation.ipynb`
- `04_state_b_fea_prompt_loader.ipynb`
- `05_manual_freecad_fea_results_entry.ipynb`
- `06_state_c_post_fea_revision.ipynb`
- `07_three_way_visual_analysis.ipynb`
- `one_sample_fea_inspection.ipynb`

Archive `notebooks/fea_replication/*.ipynb` into `notebooks/archive/2026-07/fea_replication/`. Preserve `notebooks/fea_replication/README.md` by either moving it beside the archived notebooks or replacing it with a short pointer to the archive and the new five-notebook series.

Do not delete notebook content. Do not move generated outputs. Do not treat archived notebooks as active contract notebooks.

## 9. Dependency Order

1. Start with no new helper. Build the mirror scripts directly against `src.interfaces`; create `src/notebook_series.py` only if duplicated nontrivial setup becomes unavoidable and is documented before coding it.
2. Build the five mirrored Python scripts first so every notebook has an executable parity target.
3. Create the five notebooks as thin display wrappers around the same public calls and artifact checks.
4. Update notebook contract tests to enforce five notebooks, five mirror scripts, public imports, cleared outputs, archive presence, and forbidden-pattern scans.
5. Archive old notebooks and update the archive README.
6. Update README, CODEBASE_MAP, SYSTEM_WORKFLOW_MAP, and session_state.
7. Run targeted tests and scans.

## 10. Task Complexity Budgets

| Task | Expected new functions | Max call depth | Interface form constraint |
|---|---|---|---|
| Shared notebook/script contract | 0 by default; max 3 only if justified | 3 | Re-export only if helper is created |
| Five Python mirror scripts | 0 production functions; one `main()` per script allowed | 3 | N/A |
| Five notebook wrappers | 0 production functions | 2 | Public imports only |
| Archive migration | 0 | N/A | N/A |
| Contract tests and docs alignment | 0-3 test helpers | 3 | N/A |

## 11. Integration Points

- `src.interfaces` is the only notebook import boundary.
- `src/fea_replication/` remains the owner for STEP, mesh, solver, result parsing, and parametric helpers.
- `src/cad/`, `src/prompts/`, `src/fea/`, `src/visualization/`, and `src/reports/` remain owners for existing A/B/C workflow behavior.
- `notebooks/python_scripts/` becomes the validation mirror for notebooks; notebooks should not contain logic that is absent from the corresponding script.
- `tests/test_notebook_contracts.py` is the primary guard against stale notebook inventory, deep imports, uncleared outputs, synthetic `sample_box` proof, and old artifact paths.

If this plan is wrong, likely failures are duplicated path setup across notebooks, stale archived notebooks still treated as active, or scripts and notebooks drifting apart.

## 12. Risks And Open Questions

- `ccx` may be unavailable on the executor machine. Notebook/script 03 must make this a clear environment preflight failure or skip condition defined by tests, not a silent pass.
- The current worktree contains many unrelated dirty files. The executor must not reset, clean, or overwrite them outside the explicit file list.
- Default is no new helper. A helper is allowed only if the executor documents duplicated nontrivial setup across at least three scripts or a parity-test requirement that cannot stay script-local.
- Existing AGENTS.md refers to `~/agent-governance/skills/core/*.md`, but this environment exposes installed skills as `~/agent-governance/skills/core/<skill>/SKILL.md`; executor should read the installed paths and record the mismatch if needed.

## 13. Validation Criteria

Run from the module root unless stated otherwise:

```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py tests/test_notebook_data.py tests/test_fea_replication.py -q
```

Inventory and forbidden-pattern checks:

```bash
find notebooks -maxdepth 2 \( -name "*.ipynb" -o -name "*.py" \) -print | sort
rg -n "sample_box|tempfile.mkdtemp|02_fea_ready|05_post_fea_refinement" notebooks tests
```

Expected result:

- Exactly five active top-level notebooks matching the target names.
- Exactly five mirror scripts under `notebooks/python_scripts/`.
- Archived old notebooks are present under `notebooks/archive/2026-07/`.
- Active notebooks import only `src.interfaces` or `src.runners` if runner use is explicitly justified.
- Active notebooks have cleared outputs and `execution_count: null`.
- Mirror scripts exercise the same public API calls and required artifact paths as the notebooks.
