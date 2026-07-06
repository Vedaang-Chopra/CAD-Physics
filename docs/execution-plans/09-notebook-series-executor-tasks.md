# Executor Tasks: Five-Notebook CAD-Physics Series

**Plan:** `docs/execution-plans/08-notebook-series-plan.md`  
**Status:** Ready for execution after human approval  
**Execution root:** `code_base/fea_cad_one_sample/` unless a task explicitly names repo-root docs.

## Execution Rules

- Do not improvise beyond the files listed in each task.
- Preserve unrelated dirty worktree changes.
- Do not delete notebooks; archive them under `notebooks/archive/2026-07/`.
- Do not edit generated outputs unless a task explicitly writes validation artifacts.
- Keep notebooks thin and public-import-only.
- Do not mark a task complete until its verify command passes.
- Add or update `docs/ai_context/AGENT_EXECUTION_LOG.md` after each task attempt.
- Use `/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python` for Python validation.

## Phase 1 - No-Helper Preflight And Notebook/Script Contract

**Goal:** Establish the minimum execution contract for five notebooks and five mirrored scripts while avoiding extra shared helpers unless strictly necessary.  
**Entry condition:** `08-notebook-series-plan.md` is approved.  
**Exit condition:** The executor records that existing public interfaces are sufficient without a new helper, or documents the strict necessity for `src/notebook_series.py` before creating it.

### Dependency Analysis

| Task | Reads from | Writes to | Depends on |
|---|---|---|---|
| 1.1 | `src/interfaces.py`, `src/notebook_data.py`, `src/fea_replication/`, current notebooks | Prefer no source writes; optional `src/notebook_series.py`, optional `src/interfaces.py` only if justified | none |
| 1.2 | Phase 1 outputs | `docs/ai_context/AGENT_EXECUTION_LOG.md` | 1.1 |

### Group 1-A - Sequential

### Task 1.1 - Prove No Helper Is Needed Before Creating One

**Phase:** 1  
**Parallel group:** sequential  
**Depends on:** none  
**Model hint:** complex-reasoning  
**Rate limit flag:** no  
**Fallback model:** local  
**Layer:** Layer 2/3 - Public interface and orchestration  
**File(s):**
  - `docs/ai_context/AGENT_EXECUTION_LOG.md` - modify
  - `src/notebook_series.py` - create only after documented strict necessity
  - `src/interfaces.py` - modify only for re-exports if helper is created
**What to build:** First inspect whether the five mirror scripts can stay direct and small using existing `src.interfaces` calls plus script-local setup. Default result should be "no helper created." Create `src/notebook_series.py` only if at least three scripts would otherwise duplicate nontrivial setup or artifact-check logic, or if parity tests require a shared structured return that cannot stay script-local. If a helper is created, keep it thin and compose existing public APIs without implementing domain logic.
**Function signatures (if applicable):**
```python
def run_notebook_step_00(*, module_root: Path, sample_id: str, selection_source: str, force: bool = False) -> dict[str, Any]:
    ...
```
Use analogous signatures for steps 01-04 only if the strict-necessity test passes.
**Input shape / output shape:** Inputs are explicit `Path`, sample/config strings, and booleans. Outputs are dictionaries containing status flags and artifact paths.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_interfaces.py -q
```
Expected: existing interface tests pass; new helper re-exports, if any, are covered. If no helper is created, this command should still pass unchanged.
**Checkpoint:** Phase 1 contract checkpoint  
**AGENT_EXECUTION_LOG notes:** Note the no-helper decision by default, or include the exact justification for creating a helper. Do not repeat old deep-import notebook patterns.
**Complexity budget:** 0 new functions by default; maximum 3 helper functions only if strict necessity is documented
**Max call depth:** <=3
**Interface form constraint:** Re-export only if helper is created
**Error contract:** Return `dict[str, Any]` on success; raise `FileNotFoundError` or `ValueError` for invalid required inputs
**Notebook equivalent:** No

### Task 1.2 - Phase 1 Verify-Checkpoint

**Phase:** 1  
**Parallel group:** sequential  
**Depends on:** Task 1.1  
**Model hint:** complex-reasoning  
**Rate limit flag:** no  
**Fallback model:** local  
**Layer:** Checkpoint  
**File(s):**
  - `docs/ai_context/AGENT_EXECUTION_LOG.md` - modify
**What to build:** READ the installed `verify-checkpoint` skill, then verify Phase 1 did not add domain logic to notebooks, runners, interfaces, or a new helper. If a helper exists, verify the execution log contains the strict-necessity justification. Record the checkpoint result.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** N/A
**Verify:**
```bash
test -s docs/ai_context/AGENT_EXECUTION_LOG.md
```
Expected: execution log contains the Phase 1 result.
**Checkpoint:** Phase 1 complete
**AGENT_EXECUTION_LOG notes:** Include no-helper decision or helper-created justification.
**Complexity budget:** 0 new functions
**Max call depth:** N/A
**Interface form constraint:** N/A
**Error contract:** N/A
**Notebook equivalent:** No

### *** SYNC POINT 1-A ***

- [ ] Task 1.1 verify passes.
- [ ] Task 1.2 verify passes.
- [ ] No notebook or output files were changed in Phase 1.
- [ ] No helper was created unless strict necessity was documented first.

## Phase 2 - Mirrored Python Scripts

**Goal:** Build the five executable `.py` mirrors before rewriting notebooks.  
**Entry condition:** Phase 1 checkpoint passed.  
**Exit condition:** All five scripts exist and validate expected public calls/artifact paths.

### Dependency Analysis

| Task | Reads from | Writes to | Depends on |
|---|---|---|---|
| 2.1 | `src.interfaces`, current sample/prompt notebooks | `notebooks/python_scripts/00_sample_prompt_generation.py` | Phase 1 |
| 2.2 | `src.interfaces`, load case and schemas | `notebooks/python_scripts/01_input_validation_physics_spec.py` | Phase 1 |
| 2.3 | `src.interfaces`, `src/fea_replication/mesh.py` | `notebooks/python_scripts/02_mesh_constraint_mapping.py` | 2.2 |
| 2.4 | `src.interfaces`, solver helpers | `notebooks/python_scripts/03_calculix_execution.py` | 2.3 |
| 2.5 | `src.interfaces`, results and reports helpers | `notebooks/python_scripts/04_results_feedback.py` | 2.4 |
| 2.6 | Phase 2 outputs | `docs/ai_context/AGENT_EXECUTION_LOG.md` | 2.1-2.5 |

### Group 2-A - Sequential

### Task 2.1 - Build Script 00 Sample Prompt Generation

**Phase:** 2  
**Parallel group:** sequential  
**Depends on:** Phase 1 checkpoint  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Layer 1 mirror script  
**File(s):**
  - `notebooks/python_scripts/00_sample_prompt_generation.py` - create
**What to build:** Create a CLI-friendly script that loads the fixed sample from dataset or DB, persists State A, executes/renders original CAD, writes load case and selector hints, builds the State B prompt, and generates or validates the State B revision artifact through public interfaces.
**Function signatures (if applicable):**
```python
def main() -> int:
    ...
```
**Input shape / output shape:** Environment/config/sample settings are constants or argparse flags matching notebook defaults. Output is exit code 0 plus printed artifact paths.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python notebooks/python_scripts/00_sample_prompt_generation.py --help
```
Expected: script parses and reports usage without importing private modules.
**Checkpoint:** Phase 2 script creation
**AGENT_EXECUTION_LOG notes:** Note DB access requirements and whether live LLM generation is gated or fixture-backed.
**Complexity budget:** 1 `main()` plus local display/printing helpers only
**Max call depth:** <=3
**Interface form constraint:** N/A
**Error contract:** Exit 0 on success; raise/exit non-zero on missing required artifacts
**Notebook equivalent:** Yes - `00_sample_prompt_generation.ipynb`

### Task 2.2 - Build Script 01 Input Validation Physics Spec

**Phase:** 2  
**Parallel group:** sequential  
**Depends on:** Phase 1 checkpoint  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Layer 1 mirror script  
**File(s):**
  - `notebooks/python_scripts/01_input_validation_physics_spec.py` - create
**What to build:** Validate State A/B required artifacts, load `load_case.json`, inspect selector hints, build baseline FEA replication config from the State B STEP, and print physics defaults and STEP-first paths.
**Function signatures (if applicable):**
```python
def main() -> int:
    ...
```
**Input shape / output shape:** Reads `outputs/sample_<sample_id>/` and writes/validates config summary only if the implementation plan chooses to persist one.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python notebooks/python_scripts/01_input_validation_physics_spec.py --help
```
Expected: script parses and reports usage without importing private modules.
**Checkpoint:** Phase 2 script creation
**AGENT_EXECUTION_LOG notes:** Record any missing artifact assumptions.
**Complexity budget:** 1 `main()` plus local formatting helpers only
**Max call depth:** <=3
**Interface form constraint:** N/A
**Error contract:** Exit 0 on success; raise/exit non-zero on missing required State A/B artifacts
**Notebook equivalent:** Yes - `01_input_validation_physics_spec.ipynb`

### Task 2.3 - Build Script 02 Mesh Constraint Mapping

**Phase:** 2  
**Parallel group:** sequential  
**Depends on:** Task 2.2  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Layer 1 mirror script  
**File(s):**
  - `notebooks/python_scripts/02_mesh_constraint_mapping.py` - create
**What to build:** Use `prepare_geometry_artifacts` and `generate_calculix_mesh` to create geometry and mesh summaries from the selected STEP, then print fixed/load node-set counts and preview paths.
**Function signatures (if applicable):**
```python
def main() -> int:
    ...
```
**Input shape / output shape:** Reads selected STEP and writes mesh artifacts under the selected run directory.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python notebooks/python_scripts/02_mesh_constraint_mapping.py --help
```
Expected: script parses and reports usage without importing private modules.
**Checkpoint:** Phase 2 script creation
**AGENT_EXECUTION_LOG notes:** Record `gmsh` dependency behavior.
**Complexity budget:** 1 `main()` plus local formatting helpers only
**Max call depth:** <=3
**Interface form constraint:** N/A
**Error contract:** Exit 0 on success; raise/exit non-zero on missing STEP or mesh failure
**Notebook equivalent:** Yes - `02_mesh_constraint_mapping.ipynb`

### Task 2.4 - Build Script 03 CalculiX Execution

**Phase:** 2  
**Parallel group:** sequential  
**Depends on:** Task 2.3  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Layer 1 mirror script  
**File(s):**
  - `notebooks/python_scripts/03_calculix_execution.py` - create
**What to build:** Run `run_calculix_solver` on the mesh summary when `ccx` is available. If `ccx` is missing, fail or skip according to the test contract with a clear message and no false success.
**Function signatures (if applicable):**
```python
def main() -> int:
    ...
```
**Input shape / output shape:** Reads mesh artifacts and writes solver stdout/stderr/result files when solver runs.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python notebooks/python_scripts/03_calculix_execution.py --help
```
Expected: script parses and reports usage without importing private modules.
**Checkpoint:** Phase 2 script creation
**AGENT_EXECUTION_LOG notes:** Record whether `ccx` is present on this machine.
**Complexity budget:** 1 `main()` plus local formatting helpers only
**Max call depth:** <=3
**Interface form constraint:** N/A
**Error contract:** Exit 0 only when solver run or defined preflight mode succeeds; non-zero for missing required mesh files
**Notebook equivalent:** Yes - `03_calculix_execution.ipynb`

### Task 2.5 - Build Script 04 Results Feedback

**Phase:** 2  
**Parallel group:** sequential  
**Depends on:** Task 2.4  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Layer 1 mirror script  
**File(s):**
  - `notebooks/python_scripts/04_results_feedback.py` - create
**What to build:** Parse CalculiX results if present, show pass/fail summaries, inspect manual FEA completion, and build feedback/comparison artifacts only through public interfaces.
**Function signatures (if applicable):**
```python
def main() -> int:
    ...
```
**Input shape / output shape:** Reads solver/manual FEA artifacts and writes parsed result/comparison/feedback artifacts where gates are complete.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python notebooks/python_scripts/04_results_feedback.py --help
```
Expected: script parses and reports usage without importing private modules.
**Checkpoint:** Phase 2 script creation
**AGENT_EXECUTION_LOG notes:** Record manual FEA gate behavior.
**Complexity budget:** 1 `main()` plus local formatting helpers only
**Max call depth:** <=3
**Interface form constraint:** N/A
**Error contract:** Exit 0 on valid available evidence or clearly blocked manual gate; non-zero on malformed required inputs
**Notebook equivalent:** Yes - `04_results_feedback.ipynb`

### Task 2.6 - Phase 2 Verify-Checkpoint

**Phase:** 2  
**Parallel group:** sequential  
**Depends on:** Tasks 2.1-2.5  
**Model hint:** complex-reasoning  
**Rate limit flag:** no  
**Fallback model:** local  
**Layer:** Checkpoint  
**File(s):**
  - `docs/ai_context/AGENT_EXECUTION_LOG.md` - modify
**What to build:** Verify all five scripts exist, expose `--help`, and avoid private `src.` imports.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** N/A
**Verify:**
```bash
find notebooks/python_scripts -maxdepth 1 -name "*.py" -print | sort
rg -n "from src\\.|import src\\." notebooks/python_scripts
```
Expected: exactly five scripts; imports are limited to `src.interfaces` unless a documented runner exception exists.
**Checkpoint:** Phase 2 complete
**AGENT_EXECUTION_LOG notes:** Include script inventory and import scan result.
**Complexity budget:** 0 new functions
**Max call depth:** N/A
**Interface form constraint:** N/A
**Error contract:** N/A
**Notebook equivalent:** No

### *** SYNC POINT 2-A ***

- [ ] Tasks 2.1-2.5 verify passes.
- [ ] Task 2.6 verify passes.
- [ ] Five mirror scripts exist before notebook rewriting begins.

## Phase 3 - Five Thin Notebooks

**Goal:** Create the five active notebooks as readable wrappers around the mirrored scripts/public calls.  
**Entry condition:** Phase 2 checkpoint passed.  
**Exit condition:** Five notebooks exist, have cleared outputs, and match the mirror script responsibilities.

### Dependency Analysis

| Task | Reads from | Writes to | Depends on |
|---|---|---|---|
| 3.1 | Script 00 | `notebooks/00_sample_prompt_generation.ipynb` | Phase 2 |
| 3.2 | Script 01 | `notebooks/01_input_validation_physics_spec.ipynb` | Phase 2 |
| 3.3 | Script 02 | `notebooks/02_mesh_constraint_mapping.ipynb` | Phase 2 |
| 3.4 | Script 03 | `notebooks/03_calculix_execution.ipynb` | Phase 2 |
| 3.5 | Script 04 | `notebooks/04_results_feedback.ipynb` | Phase 2 |
| 3.6 | Notebooks | `docs/ai_context/AGENT_EXECUTION_LOG.md` | 3.1-3.5 |

### Group 3-A - Parallel

Tasks 3.1-3.5 can be implemented in parallel only if each task writes exactly one notebook and does not touch shared files.

### Task 3.1 - Create Notebook 00 Sample Prompt Generation

**Phase:** 3  
**Parallel group:** 3-A  
**Depends on:** Phase 2 checkpoint  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Layer 1 - Notebook  
**File(s):**
  - `notebooks/00_sample_prompt_generation.ipynb` - create
**What to build:** Thin notebook that displays stage inputs, sample metadata, State A artifact paths, State B prompt text/path, revision code path, STEP path, and visual outputs by calling public interfaces or the matching script logic.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** Notebook cells use the same defaults and artifact paths as script 00.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q
```
Expected: notebook inventory and public-import checks pass after all Phase 3 notebooks are present.
**Checkpoint:** Phase 3 notebook creation
**AGENT_EXECUTION_LOG notes:** Record notebook has cleared outputs.
**Complexity budget:** 0 production functions
**Max call depth:** <=2
**Interface form constraint:** Public imports only
**Error contract:** Notebook raises on missing required artifacts and prints readable stage context first
**Notebook equivalent:** Yes

### Task 3.2 - Create Notebook 01 Input Validation Physics Spec

**Phase:** 3  
**Parallel group:** 3-A  
**Depends on:** Phase 2 checkpoint  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Layer 1 - Notebook  
**File(s):**
  - `notebooks/01_input_validation_physics_spec.ipynb` - create
**What to build:** Thin notebook that shows required State A/B files, physics defaults, load case JSON, selector hints, STEP-first path, and FEA replication config.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** Notebook cells use the same defaults and artifact paths as script 01.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q
```
Expected: notebook inventory and public-import checks pass after all Phase 3 notebooks are present.
**Checkpoint:** Phase 3 notebook creation
**AGENT_EXECUTION_LOG notes:** Record notebook has cleared outputs.
**Complexity budget:** 0 production functions
**Max call depth:** <=2
**Interface form constraint:** Public imports only
**Error contract:** Notebook raises on invalid/missing physics inputs and prints readable stage context first
**Notebook equivalent:** Yes

### Task 3.3 - Create Notebook 02 Mesh Constraint Mapping

**Phase:** 3  
**Parallel group:** 3-A  
**Depends on:** Phase 2 checkpoint  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Layer 1 - Notebook  
**File(s):**
  - `notebooks/02_mesh_constraint_mapping.ipynb` - create
**What to build:** Thin notebook that prepares geometry, generates mesh, displays preview images, prints node/element counts, and explains fixed/load node-set selection from existing mesh summaries.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** Notebook cells use the same defaults and artifact paths as script 02.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q
```
Expected: notebook inventory and public-import checks pass after all Phase 3 notebooks are present.
**Checkpoint:** Phase 3 notebook creation
**AGENT_EXECUTION_LOG notes:** Record notebook has cleared outputs.
**Complexity budget:** 0 production functions
**Max call depth:** <=2
**Interface form constraint:** Public imports only
**Error contract:** Notebook raises on missing STEP or mesh generation failure and prints readable stage context first
**Notebook equivalent:** Yes

### Task 3.4 - Create Notebook 03 CalculiX Execution

**Phase:** 3  
**Parallel group:** 3-A  
**Depends on:** Phase 2 checkpoint  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Layer 1 - Notebook  
**File(s):**
  - `notebooks/03_calculix_execution.ipynb` - create
**What to build:** Thin notebook that preflights `ccx`, runs the solver when available, and displays stdout/stderr/result artifact paths without claiming solver success when `ccx` is missing.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** Notebook cells use the same defaults and artifact paths as script 03.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q
```
Expected: notebook inventory and public-import checks pass after all Phase 3 notebooks are present.
**Checkpoint:** Phase 3 notebook creation
**AGENT_EXECUTION_LOG notes:** Record notebook has cleared outputs and `ccx` behavior.
**Complexity budget:** 0 production functions
**Max call depth:** <=2
**Interface form constraint:** Public imports only
**Error contract:** Notebook reports missing solver clearly or raises on malformed solver inputs
**Notebook equivalent:** Yes

### Task 3.5 - Create Notebook 04 Results Feedback

**Phase:** 3  
**Parallel group:** 3-A  
**Depends on:** Phase 2 checkpoint  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Layer 1 - Notebook  
**File(s):**
  - `notebooks/04_results_feedback.ipynb` - create
**What to build:** Thin notebook that parses available results, displays pass/fail status, shows manual FEA gate state, and builds feedback/comparison outputs only when required evidence exists.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** Notebook cells use the same defaults and artifact paths as script 04.
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q
```
Expected: notebook inventory and public-import checks pass after all Phase 3 notebooks are present.
**Checkpoint:** Phase 3 notebook creation
**AGENT_EXECUTION_LOG notes:** Record notebook has cleared outputs and manual gate behavior.
**Complexity budget:** 0 production functions
**Max call depth:** <=2
**Interface form constraint:** Public imports only
**Error contract:** Notebook reports blocked manual gate clearly and raises on malformed required inputs
**Notebook equivalent:** Yes

### *** SYNC POINT 3-A ***

- [ ] Tasks 3.1-3.5 created exactly one notebook each.
- [ ] No task touched shared docs or tests during parallel notebook creation.
- [ ] All notebooks have cleared outputs and null execution counts.

### Group 3-B - Sequential

### Task 3.6 - Phase 3 Verify-Checkpoint

**Phase:** 3  
**Parallel group:** sequential  
**Depends on:** Tasks 3.1-3.5  
**Model hint:** complex-reasoning  
**Rate limit flag:** no  
**Fallback model:** local  
**Layer:** Checkpoint  
**File(s):**
  - `docs/ai_context/AGENT_EXECUTION_LOG.md` - modify
**What to build:** Verify active notebook inventory and cleared-output/public-import rules.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** N/A
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q
```
Expected: notebook contract tests pass.
**Checkpoint:** Phase 3 complete
**AGENT_EXECUTION_LOG notes:** Include active notebook inventory.
**Complexity budget:** 0 new functions
**Max call depth:** N/A
**Interface form constraint:** N/A
**Error contract:** N/A
**Notebook equivalent:** No

### *** SYNC POINT 3-B ***

- [ ] Task 3.6 verify passes.
- [ ] Phase 3 complete before archive migration begins.

## Phase 4 - Archive And Contract Tests

**Goal:** Move old notebooks to archive and update tests/docs that enforce the new active notebook set.  
**Entry condition:** Phase 3 checkpoint passed.  
**Exit condition:** Old notebooks are archived, active contract tests target the new five-notebook series, and docs are aligned.

### Dependency Analysis

| Task | Reads from | Writes to | Depends on |
|---|---|---|---|
| 4.1 | current notebook tree | `notebooks/archive/2026-07/` | Phase 3 |
| 4.2 | new notebooks/scripts/archive | `tests/test_notebook_contracts.py` | 4.1 |
| 4.3 | new inventory | README, CODEBASE_MAP, SYSTEM_WORKFLOW_MAP, session_state | 4.2 |
| 4.4 | Phase 4 outputs | execution log | 4.1-4.3 |

### Group 4-A - Sequential

### Task 4.1 - Archive Superseded Notebooks

**Phase:** 4  
**Parallel group:** sequential  
**Depends on:** Phase 3 checkpoint  
**Model hint:** local  
**Rate limit flag:** no  
**Fallback model:** complex-reasoning  
**Layer:** Documentation/archive  
**File(s):**
  - `notebooks/archive/2026-07/README.md` - create
  - `notebooks/archive/2026-07/*.ipynb` - create by moving old notebooks
  - `notebooks/archive/2026-07/fea_replication/*.ipynb` - create by moving old replication notebooks
  - `notebooks/fea_replication/README.md` - move or replace with pointer
**What to build:** Move superseded notebooks into the archive directory and write an archive README listing original paths and replacement notebook responsibilities. Preserve content; do not delete notebook files.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** N/A
**Verify:**
```bash
find notebooks/archive/2026-07 -name "*.ipynb" -print | sort
```
Expected: old top-level notebooks and old `fea_replication` notebooks are present in archive.
**Checkpoint:** Archive migration
**AGENT_EXECUTION_LOG notes:** Include moved file inventory.
**Complexity budget:** 0 new functions
**Max call depth:** N/A
**Interface form constraint:** N/A
**Error contract:** N/A
**Notebook equivalent:** No

### Task 4.2 - Update Notebook Contract Tests

**Phase:** 4  
**Parallel group:** sequential  
**Depends on:** Task 4.1  
**Model hint:** fast-code  
**Rate limit flag:** yes  
**Fallback model:** local  
**Layer:** Tests  
**File(s):**
  - `tests/test_notebook_contracts.py` - modify
**What to build:** Update tests to require exactly the five active notebooks and five mirror scripts, cleared outputs, public imports, archive presence, forbidden-pattern scans, and notebook/script parity markers.
**Function signatures (if applicable):**
```python
def test_active_notebook_inventory_matches_five_part_series() -> None:
    ...
```
**Input shape / output shape:** N/A
**Verify:**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q
```
Expected: notebook contract tests pass.
**Checkpoint:** Contract tests
**AGENT_EXECUTION_LOG notes:** Record any intentionally archived notebook exclusions.
**Complexity budget:** up to 3 test helpers
**Max call depth:** <=3
**Interface form constraint:** N/A
**Error contract:** Tests fail with explicit filename/path messages
**Notebook equivalent:** No

### Task 4.3 - Update Documentation Maps

**Phase:** 4  
**Parallel group:** sequential  
**Depends on:** Task 4.2  
**Model hint:** local  
**Rate limit flag:** no  
**Fallback model:** complex-reasoning  
**Layer:** Documentation  
**File(s):**
  - `README.md` - modify
  - `../docs/ai_context/CODEBASE_MAP.md` - modify from module root or `docs/ai_context/CODEBASE_MAP.md` from repo root
  - `../docs/ai_context/SYSTEM_WORKFLOW_MAP.md` - modify from module root or `docs/ai_context/SYSTEM_WORKFLOW_MAP.md` from repo root
  - `../docs/session_state.md` - modify from module root or `docs/session_state.md` from repo root
**What to build:** Replace old notebook inventory with the five-notebook series, document `notebooks/python_scripts/`, record archive location, and update session state with the exact completed phase.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** N/A
**Verify:**
```bash
cd ../..
rg -n "00_sample_prompt_generation|04_results_feedback|notebooks/python_scripts|archive/2026-07" docs/ai_context docs/session_state.md code_base/fea_cad_one_sample/README.md
```
Expected: all docs mention the new series, mirror scripts, and archive.
**Checkpoint:** Docs alignment
**AGENT_EXECUTION_LOG notes:** Include docs updated.
**Complexity budget:** 0 new functions
**Max call depth:** N/A
**Interface form constraint:** N/A
**Error contract:** N/A
**Notebook equivalent:** No

### Task 4.4 - Phase 4 Verify-Checkpoint

**Phase:** 4  
**Parallel group:** sequential  
**Depends on:** Tasks 4.1-4.3  
**Model hint:** complex-reasoning  
**Rate limit flag:** no  
**Fallback model:** local  
**Layer:** Checkpoint  
**File(s):**
  - `docs/ai_context/AGENT_EXECUTION_LOG.md` - modify
**What to build:** Verify archive, tests, and docs alignment.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** N/A
**Verify:**
```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q
```
Expected: contract tests pass.
**Checkpoint:** Phase 4 complete
**AGENT_EXECUTION_LOG notes:** Include final active and archived notebook counts.
**Complexity budget:** 0 new functions
**Max call depth:** N/A
**Interface form constraint:** N/A
**Error contract:** N/A
**Notebook equivalent:** No

### *** SYNC POINT 4-A ***

- [ ] Old notebooks are archived, not deleted.
- [ ] Contract tests pass.
- [ ] Docs mention the new active series and archive location.

## Phase 5 - Final Parity Validation

**Goal:** Prove notebook/script parity and scan for stale references.  
**Entry condition:** Phase 4 checkpoint passed.  
**Exit condition:** Required tests and scans pass; final change report is written.

### Dependency Analysis

| Task | Reads from | Writes to | Depends on |
|---|---|---|---|
| 5.1 | full notebook/script/doc state | execution log, session state if needed | Phase 4 |

### Group 5-A - Sequential

### Task 5.1 - Run Final Validation And Report

**Phase:** 5  
**Parallel group:** sequential  
**Depends on:** Phase 4 checkpoint  
**Model hint:** complex-reasoning  
**Rate limit flag:** no  
**Fallback model:** local  
**Layer:** Checkpoint/final validation  
**File(s):**
  - `docs/ai_context/AGENT_EXECUTION_LOG.md` - modify
  - `docs/session_state.md` - modify only if final status changed after Task 4.3
**What to build:** Run final tests/scans, update execution log, and produce the required Change Report.
**Function signatures (if applicable):** N/A
**Input shape / output shape:** N/A
**Verify:**
```bash
cd code_base/fea_cad_one_sample
/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py tests/test_notebook_data.py tests/test_fea_replication.py -q
find notebooks -maxdepth 2 \( -name "*.ipynb" -o -name "*.py" \) -print | sort
rg -n "sample_box|tempfile.mkdtemp|02_fea_ready|05_post_fea_refinement" notebooks tests
```
Expected: pytest passes; inventory shows five active notebooks and five scripts; stale-reference scan has no matches in active notebooks/scripts/tests except explicitly archived paths if the test excludes archive.
**Checkpoint:** Feature complete
**AGENT_EXECUTION_LOG notes:** Include exact commands and results.
**Complexity budget:** 0 new functions
**Max call depth:** N/A
**Interface form constraint:** N/A
**Error contract:** N/A
**Notebook equivalent:** No

### *** SYNC POINT 5-A ***

- [ ] Final pytest command passes.
- [ ] Inventory check passes.
- [ ] Forbidden-pattern scan passes for active notebooks/scripts/tests.
- [ ] Change Report includes files modified, docs updated, diagrams updated, validation run, validation not run, known limitations, and execution log update.

## Checkpoint Coverage Audit

- [x] Every touched module with interface impact has a task covering `src/interfaces.py`.
- [x] Every required notebook/script output file has an owning task.
- [x] Every behavior in the approved plan appears in at least one task.
- [x] Every phase has a verify-checkpoint task.
- [x] Every parallel group has a sync point.
- [x] Known failed patterns are noted: `sample_box`, deep notebook imports, old output paths, hidden solver assumptions, and copied CAD Design runtime coupling.
- [x] Every task has model hint and fallback.
- [x] Free-tier tasks in the same parallel group touch separate notebooks only.
- [x] Interface tasks include interface form constraints.
- [x] New public helpers are avoided by default; if any are created, strict necessity and error contracts are documented.
- [x] Every notebook task has a mirrored script requirement.

## Sequential Execution Prompt

Use `docs/execution-plans/06-pi-sequential-execution-prompt.md` as the base execution loop. Override its task path with this file:

```text
docs/execution-plans/09-notebook-series-executor-tasks.md
```

At each task, read the task entry fully, execute only the listed files, run the verify command, fix failures before proceeding, update `docs/ai_context/AGENT_EXECUTION_LOG.md`, and stop at every phase checkpoint for human confirmation.
