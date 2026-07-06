# Agent Execution Log
# Location: docs/ai_context/AGENT_EXECUTION_LOG.md
# Updated by: every agent, after every task attempt (success or failure)
# Read by:    every agent, before starting any task
#
# PURPOSE: Prevent repeated mistakes across sessions and across models.
# If an approach is marked FAILED, do not repeat it without explicit human override.

---

## HOW TO USE THIS LOG

### Before starting any task
1. Open this file.
2. Search for entries matching the files, modules, or approach you plan to use.
3. If a FAILED entry exists for your planned approach: use the Resolution instead.
4. If no entry exists: proceed, but write one after completing.

### After completing or failing any task
Add an entry at the top of the Entries section using the template below.
Do not skip this step. It is a required output of every task.

---

## Entry Template

Copy this block and fill it in. Add at the TOP of the Entries section.

```markdown
## [TASK_ID] — [Task name]
**Date:** YYYY-MM-DD
**Agent:** Pi | Codex | Claude Code
**Model:** [model name actually used]
**Status:** ✓ Complete | ✗ Failed | ⚠ Partial

**Approach taken:**
[1–3 sentences describing what was tried]

**What worked:**
[Specific things that succeeded — be concrete]

**What failed:**
[Specific things that failed — include exact error messages or symptoms]

**Root cause:**
[Why it failed — be specific. "Wrong import path" not just "import error"]

**Resolution:**
[What fixed it, or what the next agent should try instead]

**Files modified:**
- `path/to/file.py`

**Verify result:**
[Exact command and output, or "Verification not run — reason"]

**Model fallback used:** yes | no
[If yes: which model was tried first, why it failed, what fallback was used]

**DO NOT REPEAT:**
[Specific anti-patterns, import paths, approaches that failed for this task/module]
```

---

## Entries

## 3.6 — Phase 3 Verify-Checkpoint
**Date:** 2026-07-05
**Agent:** Pi
**Model:** GPT-5
**Status:** ✗ Failed

**Approach taken:**
Ran the notebook contract verification after creating the five new thin notebooks. The notebook files themselves are structurally valid, but the current contract test still targets the old active notebook inventory and the legacy notebooks remain present.

**What worked:**
The new notebook JSON files were written and a standalone syntax-compile sweep over their code cells passed.

**What failed:**
`pytest tests/test_notebook_contracts.py -q` failed with `AssertionError: assert False` on the old expected notebook set, plus `FileNotFoundError` for `00_select_real_sample.ipynb` through `05_final_abc_comparison.ipynb` because those notebooks are no longer active in this phase.

**Root cause:**
The contract test is still aligned to the pre-series notebook inventory. Phase 4 archive/migration and test updates are needed before this checkpoint can pass.

**Resolution:**
Stop before marking Phase 3 complete. Update the contract test and archive the superseded notebooks in the next phase, then rerun the checkpoint.

**Files modified:**
- `docs/ai_context/AGENT_EXECUTION_LOG.md`

**Verify result:**
`cd code_base/fea_cad_one_sample && /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_notebook_contracts.py -q` → failed (9 failed)

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not expect Phase 3 checkpoint to pass before the notebook inventory test is updated.
- Do not treat the old notebook set as active once the new series is present.

## 3.1-3.5 — Create Thin Notebooks
**Date:** 2026-07-05
**Agent:** Pi
**Model:** GPT-5
**Status:** ⚠ Partial

**Approach taken:**
Created five thin notebook wrappers for the new series and kept them public-interface-only. Each notebook now mirrors the corresponding script at a high level, prints stage markers, shows artifact paths, includes assertions, and demonstrates a failure case.

**What worked:**
The five new notebooks were written successfully and a syntax-compile sweep over all new notebook code cells passed.

**What failed:**
The phase-3 contract check could not pass yet because `tests/test_notebook_contracts.py` still expects the old active notebook inventory and the old notebooks are still present.

**Root cause:**
Notebook creation is complete, but the active notebook contract has not been migrated to the new five-notebook series.

**Resolution:**
Proceed to the archive + contract-test update phase before retrying the notebook checkpoint.

**Files modified:**
- `code_base/fea_cad_one_sample/notebooks/00_sample_prompt_generation.ipynb`
- `code_base/fea_cad_one_sample/notebooks/01_input_validation_physics_spec.ipynb`
- `code_base/fea_cad_one_sample/notebooks/02_mesh_constraint_mapping.ipynb`
- `code_base/fea_cad_one_sample/notebooks/03_calculix_execution.ipynb`
- `code_base/fea_cad_one_sample/notebooks/04_results_feedback.ipynb`
- `docs/ai_context/AGENT_EXECUTION_LOG.md`

**Verify result:**
`/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python - <<'PY' ... compile notebook code cells ... PY` → passed; `pytest tests/test_notebook_contracts.py -q` → failed (old inventory)

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not use the old notebook inventory as the active contract.
- Do not skip the archive step for the superseded notebooks.

## 2.1 — Build Script 00 Sample Prompt Generation
**Date:** 2026-07-05
**Agent:** Pi
**Model:** GPT-5
**Status:** ✓ Complete

**Approach taken:**
Created a direct notebook mirror script under `notebooks/python_scripts/` that bootstraps `src` onto `sys.path`, uses only `src.interfaces`, and implements the full State A → State B artifact flow with CLI flags.

**What worked:**
`--help` runs successfully from the module root, and the script exposes the expected sample, source, config, and force flags without importing private modules.

**What failed:**
Nothing material.

**Root cause:**
N/A — script creation succeeded.

**Resolution:**
Keep the mirror direct and public-interface-only; no shared helper was needed.

**Files modified:**
- `code_base/fea_cad_one_sample/notebooks/python_scripts/00_sample_prompt_generation.py`
- `docs/ai_context/AGENT_EXECUTION_LOG.md`

**Verify result:**
`cd code_base/fea_cad_one_sample && /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python notebooks/python_scripts/00_sample_prompt_generation.py --help` → passed

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not import private `src.*` modules from notebook mirrors.
- Do not add a shared notebook helper unless duplication becomes unavoidable.

## 2.2 — Build Script 01 Input Validation Physics Spec
**Date:** 2026-07-05
**Agent:** Pi
**Model:** GPT-5
**Status:** ✓ Complete

**Approach taken:**
Created a direct mirror script for the State A/B validation notebook that uses only `src.interfaces`, checks the required artifact tree, loads load-case and selector-hint JSON, and prints baseline physics defaults from the public config builder.

**What worked:**
`--help` runs successfully from the module root, and the script exposes the sample, config, and force flags without private imports.

**What failed:**
Nothing material.

**Root cause:**
N/A — script creation succeeded.

**Resolution:**
Keep the mirror public-interface-only and validate existing artifact paths before any deeper physics checks.

**Files modified:**
- `code_base/fea_cad_one_sample/notebooks/python_scripts/01_input_validation_physics_spec.py`
- `docs/ai_context/AGENT_EXECUTION_LOG.md`

**Verify result:**
`cd code_base/fea_cad_one_sample && /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python notebooks/python_scripts/01_input_validation_physics_spec.py --help` → passed

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not import anything below `src.interfaces` from the mirror.
- Do not skip required-artifact checks in the validation mirror.

## 2.3 — Build Script 02 Mesh Constraint Mapping
**Date:** 2026-07-05
**Agent:** Pi
**Model:** GPT-5
**Status:** ✓ Complete

**Approach taken:**
Created the mesh/constraint mirror script as a thin public-interface wrapper that bootstraps `src`, builds the baseline FEA replication config, prepares geometry artifacts, and generates the mesh and region-selection summaries.

**What worked:**
`--help` runs successfully from the module root, and the mirror exposes the sample and force flags without private imports.

**What failed:**
Nothing material.

**Root cause:**
N/A — script creation succeeded.

**Resolution:**
Keep mesh generation in the public FEA replication surface; the mirror should only orchestrate and print artifact paths.

**Files modified:**
- `code_base/fea_cad_one_sample/notebooks/python_scripts/02_mesh_constraint_mapping.py`
- `docs/ai_context/AGENT_EXECUTION_LOG.md`

**Verify result:**
`cd code_base/fea_cad_one_sample && /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python notebooks/python_scripts/02_mesh_constraint_mapping.py --help` → passed

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not add any mesh logic below `src.interfaces` in the mirror.
- Do not bury region-selection details in a shared helper.

## 2.4 — Build Script 03 CalculiX Execution
**Date:** 2026-07-05
**Agent:** Pi
**Model:** GPT-5
**Status:** ✓ Complete

**Approach taken:**
Created the CalculiX execution mirror as a thin public-interface wrapper that bootstraps `src`, loads the mesh summary from disk, preflights `ccx`, and runs the solver only when the executable is present.

**What worked:**
`--help` runs successfully from the module root, and the mirror exposes the sample and force flags without private imports.

**What failed:**
Nothing material.

**Root cause:**
N/A — script creation succeeded.

**Resolution:**
Keep solver invocation behind the public FEA replication interface and preserve the explicit `ccx` preflight message.

**Files modified:**
- `code_base/fea_cad_one_sample/notebooks/python_scripts/03_calculix_execution.py`
- `docs/ai_context/AGENT_EXECUTION_LOG.md`

**Verify result:**
`cd code_base/fea_cad_one_sample && /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python notebooks/python_scripts/03_calculix_execution.py --help` → passed

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not claim solver success when `ccx` is missing.
- Do not import solver internals directly from the mirror.

## 2.5 — Build Script 04 Results Feedback
**Date:** 2026-07-05
**Agent:** Pi
**Model:** GPT-5
**Status:** ✓ Complete

**Approach taken:**
Created the results/feedback mirror as a thin public-interface wrapper that bootstraps `src`, parses solver results when present, checks the manual FEA gate, and conditionally promotes State C through the public interfaces.

**What worked:**
`--help` runs successfully from the module root, and the mirror exposes the sample and force flags without private imports.

**What failed:**
Nothing material.

**Root cause:**
N/A — script creation succeeded.

**Resolution:**
Keep comparison, reporting, and State C promotion behind public interfaces and only proceed when manual evidence is complete.

**Files modified:**
- `code_base/fea_cad_one_sample/notebooks/python_scripts/04_results_feedback.py`
- `docs/ai_context/AGENT_EXECUTION_LOG.md`

**Verify result:**
`cd code_base/fea_cad_one_sample && /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python notebooks/python_scripts/04_results_feedback.py --help` → passed

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not treat missing manual evidence as success.
- Do not import comparison/report internals directly from the mirror.

## 2.6 — Phase 2 Verify-Checkpoint
**Date:** 2026-07-05
**Agent:** Pi
**Model:** GPT-5
**Status:** ✓ Complete

**Approach taken:**
Verified the mirrored-script inventory and import surface after creating the five CLI mirrors. The checkpoint scan checked that only the five expected scripts exist and that they do not use private `src.` imports.

**What worked:**
The inventory shows exactly five Python mirror scripts, and the private-import scan returned no matches.

**What failed:**
Nothing material.

**Root cause:**
N/A — checkpoint passed.

**Resolution:**
Phase 2 scripts are complete; stop before notebook rewriting until the phase-gate summary is acknowledged.

**Files modified:**
- `docs/ai_context/AGENT_EXECUTION_LOG.md`

**Verify result:**
`find notebooks/python_scripts -maxdepth 1 -name "*.py" -print | sort` and `rg -n "from src\\.|import src\\." notebooks/python_scripts` → passed (5 scripts; no matches)

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not add extra mirror scripts beyond the five-task series.
- Do not introduce private `src.` imports into notebook mirrors.

## 1.2 — Phase 1 Verify-Checkpoint
**Date:** 2026-07-05
**Agent:** Pi
**Model:** GPT-5
**Status:** ✓ Complete

**Approach taken:**
Verified the Phase 1 checkpoint requirement after confirming no helper was created. The checkpoint check only needed the execution log to be present and the phase decision to be documented.

**What worked:**
The execution log contains the no-helper decision, and the checkpoint file is non-empty.

**What failed:**
Nothing material.

**Root cause:**
N/A — checkpoint passed.

**Resolution:**
Phase 1 is complete; stop here and await phase-gate confirmation before starting Phase 2.

**Files modified:**
- `docs/ai_context/AGENT_EXECUTION_LOG.md`

**Verify result:**
`test -s docs/ai_context/AGENT_EXECUTION_LOG.md` → passed

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not begin Phase 2 before the phase-gate summary is acknowledged.
- Do not create `src/notebook_series.py` without documented strict necessity.

## 1.1 — Prove No Helper Is Needed Before Creating One
**Date:** 2026-07-05
**Agent:** Pi
**Model:** GPT-5
**Status:** ✓ Complete

**Approach taken:**
Reviewed the approved notebook-series plan, the executor tasks, the public `src.interfaces` surface, notebook helpers, the fea-replication package, and the current notebook inventory to determine whether the five mirror scripts need a shared helper layer.

**What worked:**
The existing public interfaces already expose the notebook-visible actions needed for the five scripts, and script-local setup is sufficient for path resolution, display, and artifact checks.

**What failed:**
Nothing material; no helper was needed.

**Root cause:**
The planned notebook/script boundary is already thin enough that a shared `src/notebook_series.py` would only duplicate path and orchestration glue.

**Resolution:**
Do not create `src/notebook_series.py` in Phase 1. Keep the five mirrors direct against `src.interfaces` unless a later task proves strict necessity.

**Files modified:**
- `docs/ai_context/AGENT_EXECUTION_LOG.md`

**Verify result:**
`cd code_base/fea_cad_one_sample && /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_interfaces.py -q` → passed (1 passed)

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not create `src/notebook_series.py` preemptively.
- Do not add shared helper glue unless at least three mirrors truly need the same nontrivial setup.
- Do not bypass the public `src.interfaces` boundary from notebooks/scripts.

<!-- Example entry — delete when real entries are added:

## EXAMPLE-1 — Build repair loop core
**Date:** 2026-06-01
**Agent:** Pi
**Model:** qwen2.5-coder:7b (local)
**Status:** ⚠ Partial

**Approach taken:**
Implemented the repair loop using a recursive call structure within `repair_loop.py`.

**What worked:**
The incremental B-Rep trajectory analysis logic was correct.
Logging with `getLogger(__name__)` worked cleanly.

**What failed:**
Import of `BRepUtils` from `src/cad_design/core/brep_utils.py` raised ModuleNotFoundError.
The CODEBASE_MAP.md had a stale path — `brep_utils` had moved to `src/utils/brep/`.

**Root cause:**
CODEBASE_MAP.md was not updated when brep_utils was refactored last session.

**Resolution:**
Corrected import to `from src.utils.brep.brep_utils import BRepUtils`.
Updated CODEBASE_MAP.md to reflect current location.

**Files modified:**
- `src/repair/repair_loop.py`
- `docs/ai_context/CODEBASE_MAP.md`

**Verify result:**
`pytest tests/test_repair_loop.py -v` → 8/8 passing

**Model fallback used:** no

**DO NOT REPEAT:**
- Do not import BRepUtils from `src/cad_design/core/`. It lives in `src/utils/brep/`.
- Do not trust CODEBASE_MAP.md without cross-checking against actual file tree for brep utilities.

-->
