# Pi Microtasks: One-Sample CADCodeVerify to FEA-Ready CAD

**Spec:** `docs/execution-plans/01-basic-sample-fea-confirmed-spec.md`  
**Architecture:** `docs/execution-plans/02-basic-sample-fea-architecture.md`  
**Status:** In Progress  
**Current Phase:** 6  

## Rules For Pi

- Preserve the main intent from `conversations/01-start.md`: this is a physics-aware CAD prototype, not a generic CAD export tool.
- Execute phases in order.
- Execute tasks in order unless marked `[P]`.
- Do not mark a task complete until its verify command passes.
- Do not begin the next phase until the checkpoint passes.
- Update `docs/session_state.md` after every phase and before stopping.
- From Phase 2 onward, `cd code_base/fea_cad_one_sample` before task execution unless a task explicitly says otherwise.
- From Phase 2 onward, every `src/...`, `tests/...`, `notebooks/...`, and `outputs/...` path in this file is relative to `code_base/fea_cad_one_sample/`.
- Every implementation task must also create or update the named test file in the same task.

---

## Phase 0: Runtime Environment

**Purpose:** create a dedicated runtime that can execute CadQuery, OpenAI calls, rendering, DB access, and tests.  
**Required skills:** `discover-codebase`, `verify-checkpoint`, `handoff-coding-agent` if stopping.  
**Depends on:** nothing.

- [x] **Task 0.1 — Create `cad_physics` environment**
  - Run:

    ```bash
    conda create -n cad_physics --clone cadquery -y
    ```

  - Verify:

    ```bash
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python - <<'PY'
    import cadquery, openai, trimesh, pandas, sqlalchemy, psycopg2, pytest
    print("cad_physics ready")
    PY
    ```

  - Tracking update: record env creation status in `docs/session_state.md`.

### Checkpoint 0

- [ ] `cadquery`, `openai`, `trimesh`, `pandas`, `sqlalchemy`, `psycopg2`, and `pytest` import successfully in `cad_physics`.
- [ ] `docs/session_state.md` records Phase 0 status.

---

## Phase 1: Planning And Tracking Files

**Purpose:** make the execution documents and tracking files real before code generation starts.  
**Required skills:** `write-spec`, `write-plan`, `decompose-tasks`, `update-codebase-map`, `handoff-coding-agent` if stopping.  
**Depends on:** Phase 0 checkpoint.

- [x] **Task 1.1 — Confirm execution docs exist**
  - Check these files:

    ```text
    docs/execution-plans/00-pi-execution-protocol.md
    docs/execution-plans/01-basic-sample-fea-confirmed-spec.md
    docs/execution-plans/02-basic-sample-fea-architecture.md
    docs/execution-plans/03-basic-sample-fea-pi-microtasks.md
    docs/execution-plans/04-basic-sample-fea-checkpoints.md
    docs/execution-plans/05-basic-sample-fea-handoff-template.md
    docs/execution-plans/06-pi-sequential-execution-prompt.md
    ```

  - Verify:

    ```bash
    test -s docs/execution-plans/00-pi-execution-protocol.md
    test -s docs/execution-plans/01-basic-sample-fea-confirmed-spec.md
    test -s docs/execution-plans/02-basic-sample-fea-architecture.md
    test -s docs/execution-plans/03-basic-sample-fea-pi-microtasks.md
    test -s docs/execution-plans/04-basic-sample-fea-checkpoints.md
    test -s docs/execution-plans/05-basic-sample-fea-handoff-template.md
    test -s docs/execution-plans/06-pi-sequential-execution-prompt.md
    ```

- [x] **Task 1.2 — Create or update tracking docs**
  - Create/update:

    ```text
    docs/session_state.md
    docs/ai_context/DOC_TAXONOMY.md
    docs/ai_context/CODEBASE_MAP.md
    docs/ai_context/SYSTEM_WORKFLOW_MAP.md
    ```

  - Verify:

    ```bash
    test -s docs/session_state.md
    test -s docs/ai_context/DOC_TAXONOMY.md
    test -s docs/ai_context/CODEBASE_MAP.md
    test -s docs/ai_context/SYSTEM_WORKFLOW_MAP.md
    ```

- [x] **Task 1.3 — Unresolved marker scan**
  - Verify:

    ```bash
    python3 - <<'PY'
    from pathlib import Path
    terms = ["T" + "BD", "TO" + "DO", "fill" + " in", "place" + "holder"]
    roots = [Path("docs/execution-plans"), Path("docs/ai_context"), Path("docs/session_state.md")]
    hits = []
    for root in roots:
        files = [root] if root.is_file() else sorted(root.rglob("*.md"))
        for path in files:
            text = path.read_text(encoding="utf-8")
            for term in terms:
                if term in text:
                    hits.append(f"{path}: contains unresolved marker {term!r}")
    if hits:
        raise SystemExit("\n".join(hits))
    PY
    ```

  - If the command finds intentional future-work wording, replace it with exact instructions.

### Checkpoint 1

- [x] All planning files exist and are non-empty.
- [x] `docs/ai_context/DOC_TAXONOMY.md` exists and defines documentation authority.
- [x] No unresolved marker text exists.
- [x] `docs/session_state.md` records Phase 1 status.

---

## Phase 2: Module Skeleton

**Purpose:** create the standalone project structure with correct layers.  
**Required skills:** `create-module`, `design-layered-module`, `write-module-readme`, `update-codebase-map`, `update-system-diagram`, `verify-checkpoint`.  
**Depends on:** Phase 1 checkpoint.

- [x] **Task 2.1 — Create module directories**
  - Create:

    ```text
    code_base/fea_cad_one_sample/
    code_base/fea_cad_one_sample/notebooks/
    code_base/fea_cad_one_sample/outputs/
    code_base/fea_cad_one_sample/src/
    code_base/fea_cad_one_sample/src/schemas/
    code_base/fea_cad_one_sample/src/orchestration/
    code_base/fea_cad_one_sample/src/db/
    code_base/fea_cad_one_sample/src/cad/
    code_base/fea_cad_one_sample/src/prompts/
    code_base/fea_cad_one_sample/src/visualization/
    code_base/fea_cad_one_sample/src/fea/
    code_base/fea_cad_one_sample/src/reports/
    code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/
    code_base/fea_cad_one_sample/tests/
    ```

  - Verify:

    ```bash
    test -d code_base/fea_cad_one_sample/src/orchestration
    test -d code_base/fea_cad_one_sample/src/copied_from_cadcodeverify
    test -d code_base/fea_cad_one_sample/tests
    ```

- [x] **Task 2.2 — Add base package files**
  - Create:

    ```text
    code_base/fea_cad_one_sample/README.md
    code_base/fea_cad_one_sample/pyproject.toml
    code_base/fea_cad_one_sample/requirements.txt
    code_base/fea_cad_one_sample/src/__init__.py
    code_base/fea_cad_one_sample/src/interfaces.py
    code_base/fea_cad_one_sample/src/runners.py
    code_base/fea_cad_one_sample/src/main.py
    ```

  - Add empty `__init__.py` files in each package subdirectory.
  - Verify:

    ```bash
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m compileall code_base/fea_cad_one_sample
    ```

- [x] **Task 2.3 — Write module README**
  - `README.md` must include purpose, ownership boundaries, entry points, run commands, and a Mermaid layer diagram.
  - Verify:

    ```bash
    rg -n "flowchart TD|Entry Points|How to Run" code_base/fea_cad_one_sample/README.md
    ```

### Checkpoint 2

- [x] Module directories exist.
- [x] Base files exist.
- [x] `compileall` passes.
- [x] README includes Mermaid layer diagram.
- [x] `docs/session_state.md` records Phase 2 status.

---

## Phase 3: Schemas And Config

**Purpose:** define shared data contracts and config loading before writing core logic.  
**Required skills:** `design-python-code`, `add-observability`, `write-tests`, `verify-checkpoint`.  
**Depends on:** Phase 2 checkpoint.

- [ ] **Task 3.1 — Add schema dataclasses**
  - Files:

    ```text
    code_base/fea_cad_one_sample/src/schemas/sample.py
    code_base/fea_cad_one_sample/src/schemas/config.py
    code_base/fea_cad_one_sample/src/schemas/fea.py
    code_base/fea_cad_one_sample/src/schemas/pipeline.py
    ```

  - Implement:
    - `CADSample`
    - `PipelineConfig`
    - `LoadCase`
    - `ManualFEAReport`
    - `PipelineSummary`
    - `RunManifestRecord`
  - Test file:

    ```text
    tests/test_schemas.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_schemas.py -q
    ```

- [ ] **Task 3.2 — Copy allowed config YAMLs**
  - Copy:

    ```text
    /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/config/config_gpt_5_4_mini.yaml
    /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/config/config_gptoss_openrotuer.yaml
    /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/config/config_qwen_coder.yaml
    ```

  - Destination:

    ```text
    code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/configs/
    ```

  - Verify:

    ```bash
    test -s code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/configs/config_gpt_5_4_mini.yaml
    test -s code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/configs/config_gptoss_openrotuer.yaml
    test -s code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/configs/config_qwen_coder.yaml
    ```

- [ ] **Task 3.3 — Add local config loader wrapper**
  - File:

    ```text
    code_base/fea_cad_one_sample/src/config.py
    ```

  - Behavior:
    - Default config name is `config_gpt_5_4_mini.yaml`.
    - Expand environment variables in YAML values.
    - Raise a clear error if the config file is missing.
  - Test file:

    ```text
    tests/test_config.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_config.py -q
    ```

### Checkpoint 3

- [ ] Schema tests pass.
- [ ] Config tests pass.
- [ ] Three allowed config files exist.
- [ ] `docs/session_state.md` records Phase 3 status.

---

## Phase 4: Copied Reference Code

**Purpose:** bring in minimal CAD Design reference code without making CAD Design a runtime dependency.  
**Required skills:** `discover-codebase`, `add-observability` for wrappers, `write-tests`, `verify-checkpoint`.  
**Depends on:** Phase 3 checkpoint.

- [ ] **Task 4.1 — Inspect CAD Design source paths**
  - Inspect every path listed in `02-basic-sample-fea-architecture.md`.
  - Record selected copy list in `code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/README.md`.
  - Verify:

    ```bash
    rg -n "CAD Design source inventory|Copied files" code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/README.md
    ```

- [ ] **Task 4.2 — Copy DB/config helpers**
  - Copy only needed helpers into:

    ```text
    src/copied_from_cadcodeverify/db/
    ```

  - Start from:

    ```text
    /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/config_loader.py
    /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/db/
    /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/load_data/
    ```

  - Add top-of-file source-path comments.
  - Verify:

    ```bash
    rg -n "Copied from CAD Design:" code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/db
    ```

- [ ] **Task 4.3 — Copy LLM/generation helpers**
  - Copy only needed helpers into:

    ```text
    src/copied_from_cadcodeverify/llm/
    src/copied_from_cadcodeverify/generation/
    ```

  - Start from:

    ```text
    /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/llm/
    /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/generation/
    ```

  - Add top-of-file source-path comments.
  - Verify:

    ```bash
    rg -n "Copied from CAD Design:" code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/llm code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/generation
    ```

- [ ] **Task 4.4 — Copy execution/rendering helpers**
  - Copy only needed helpers into:

    ```text
    src/copied_from_cadcodeverify/execution/
    src/copied_from_cadcodeverify/rendering/
    ```

  - Start from:

    ```text
    /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/evaluation/python_kernel.py
    /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/visual_analysis/rendering/
    ```

  - Add top-of-file source-path comments.
  - Verify:

    ```bash
    rg -n "Copied from CAD Design:" code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/execution code_base/fea_cad_one_sample/src/copied_from_cadcodeverify/rendering
    ```

### Checkpoint 4

- [ ] Copied source inventory exists.
- [ ] Every copied Python file has a source-path comment.
- [ ] Copied code compiles:

  ```bash
  /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m compileall code_base/fea_cad_one_sample/src/copied_from_cadcodeverify
  ```

- [ ] `docs/session_state.md` records Phase 4 status.

---

## Phase 5: DB Expert Prompt Loader

**Purpose:** load one expert prompt sample safely from the DB.  
**Required skills:** `add-observability`, `write-tests`, `verify-checkpoint`.  
**Depends on:** Phase 4 checkpoint.

- [x] **Task 5.1 — Implement schema inspection**
  - File:

    ```text
    src/db/schema_inspection.py
    ```

  - Function:

    ```python
    inspect_schema(connection_string: str) -> dict
    ```

  - Behavior:
    - Inspect tables and columns.
    - Do not assume DB schema before inspection.
    - Return a serializable dict.
  - Test file:

    ```text
    tests/test_db_loading.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_db_loading.py -q
    ```

- [x] **Task 5.2 — Implement expert sample selection**
  - File:

    ```text
    src/db/load_sample.py
    ```

  - Functions:

    ```python
    load_sample(connection_string: str, sample_id: str | None = None, random: bool = False, expert_random: bool = False) -> CADSample
    load_sample_by_id(connection_string: str, sample_id: str) -> CADSample
    load_random_sample(connection_string: str) -> CADSample
    load_expert_random_sample(connection_string: str) -> CADSample
    ```

  - Behavior:
    - Prefer `master_metadata.expert_prompt` if present.
    - Filter expert-random toward FEA-sensible prompt terms.
    - Keep GT code as optional metadata only.
    - `load_sample(...)` must enforce the same single-selection rule used by the CLI.
  - Test file:

    ```text
    tests/test_db_loading.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_db_loading.py -q
    ```

- [x] **Task 5.3 — Add CLI schema command**
  - Command:

    ```bash
    python -m src.main inspect-schema --config config_gpt_5_4_mini.yaml
    ```

  - Behavior:
    - Requires DB connection env var.
    - Prints table/column summary.
  - Verify with DB env set:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m src.main inspect-schema --config config_gpt_5_4_mini.yaml
    ```

### Checkpoint 5

- [x] DB loader unit tests pass.
- [x] `inspect-schema` works when `CAD_DB_CONNECTION_STRING` is set.
- [x] Missing DB env var produces a clear error.
- [x] `docs/session_state.md` records Phase 5 status.

---

## Phase 6: Baseline CAD Generation And Export

**Purpose:** generate baseline CadQuery from expert prompt and export original STEP/STL.  
**Required skills:** `design-runner`, `add-observability`, `write-tests`, `verify-checkpoint`.  
**Depends on:** Phase 5 checkpoint.

- [x] **Task 6.1 — Implement baseline generation wrapper**
  - File:

    ```text
    src/cad/generate_original.py
    src/cad/validate_cad_script.py
    ```

  - Function:

    ```python
    generate_original_code(sample: CADSample, config: PipelineConfig) -> str
    ```

  - Behavior:
    - Use copied generation/LLM wrapper.
    - Use `validate_cad_script.py` for extraction or validation of returned CadQuery code.
    - Save raw response as artifact if available.
    - Return runnable CadQuery code.
  - Test file:

    ```text
    tests/test_generate_original.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_generate_original.py -q
    ```

- [x] **Task 6.2 — Implement CadQuery execution/export**
  - Files:

    ```text
    src/cad/execute_cadquery.py
    src/cad/export_geometry.py
    ```

  - Function:

    ```python
    execute_and_export_cadquery(code: str, output_dir: Path, basename: str, force: bool = False) -> dict
    ```

  - Behavior:
    - Execute in isolated output directory.
    - Detect `result` or last valid CadQuery object.
    - Export STEP first and STL second.
    - Write `execution_log.txt`.
    - Do not overwrite existing outputs unless `force=True`.
  - Test file:

    ```text
    tests/test_cad_execution.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_cad_execution.py -q
    ```

- [x] **Task 6.3 — Add overwrite guard behavior**
  - Behavior:
    - Baseline write paths preserve existing outputs unless `force=True`.
    - The later CLI must expose `--force` and pass it through consistently.
  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_cad_execution.py tests/test_cli.py -q
    ```

### Checkpoint 6

- [x] Generation tests pass with model calls mocked.
- [x] Simple known CadQuery box exports STEP and STL.
- [x] Execution log is written.
- [x] Existing outputs are preserved unless `force=True`.
- [x] `docs/session_state.md` records Phase 6 status.

---

## Phase 7: FEA Prompt And Load Case

**Purpose:** produce FEA-ready prompt and structured load-case JSON.  
**Required skills:** `design-python-code`, `add-observability`, `write-tests`, `verify-checkpoint`.  
**Depends on:** Phase 6 checkpoint.

- [ ] **Task 7.1 — Implement FEA prompt templates**
  - Files:

    ```text
    src/prompts/prompt_templates.py
    src/prompts/build_fea_prompt.py
    ```

  - Function:

    ```python
    build_fea_prompt(sample: CADSample, load_case: LoadCase) -> str
    ```

  - Required prompt content:
    - material,
    - Young's modulus,
    - Poisson's ratio,
    - yield strength,
    - fixed/support region,
    - load region,
    - force magnitude and direction,
    - max displacement,
    - safety factor,
    - meshability,
    - STEP export,
    - single connected solid.
  - Test file:

    ```text
    tests/test_fea_prompt.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_fea_prompt.py -q
    ```

- [ ] **Task 7.2 — Implement load case writer**
  - File:

    ```text
    src/fea/write_load_case.py
    ```

  - Function:

    ```python
    write_load_case(sample_id: str, output_path: Path) -> LoadCase
    ```

  - Behavior:
    - Uses Aluminum 6061-T6 defaults.
    - Computes `max_von_mises_pa` as `138000000`.
    - Writes JSON.
  - Test file:

    ```text
    tests/test_load_case.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_load_case.py -q
    ```

### Checkpoint 7

- [ ] FEA prompt tests pass.
- [ ] Load case tests pass.
- [ ] `max_von_mises_pa` is exactly `138000000`.
- [ ] `docs/session_state.md` records Phase 7 status.

---

## Phase 8: FEA-Ready CAD Generation

**Purpose:** generate, execute, and export FEA-ready CadQuery code.  
**Required skills:** `add-observability`, `write-tests`, `verify-checkpoint`.  
**Depends on:** Phase 7 checkpoint.

- [ ] **Task 8.1 — Implement FEA-ready generation wrapper**
  - Files:

    ```text
    src/cad/generate_fea_ready.py
    src/cad/validate_cad_script.py
    ```

  - Function:

    ```python
    generate_fea_ready_code(fea_ready_prompt: str, config: PipelineConfig) -> str
    ```

  - Behavior:
    - Use copied generation code through local wrapper.
    - Use `validate_cad_script.py` for extraction or validation of returned CadQuery code.
    - Save `02_fea_ready/fea_ready_code.py`.
    - On failure, write readable failure artifact.
  - Test file:

    ```text
    tests/test_generate_fea_ready.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_generate_fea_ready.py -q
    ```

- [ ] **Task 8.2 — Reuse execution/export for FEA-ready geometry**
  - Behavior:
    - Save `fea_ready.step`, `fea_ready.stl`, and `execution_log.txt`.
    - Preserve previous outputs on failure.
  - Test file:

    ```text
    tests/test_generate_fea_ready.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_generate_fea_ready.py -q
    ```

### Checkpoint 8

- [ ] FEA-ready generation stage tests pass.
- [ ] Failure path writes readable log and preserves prior outputs.
- [ ] `docs/session_state.md` records Phase 8 status.

---

## Phase 9: Rendering And Comparison

**Purpose:** render original and FEA-ready STL files and build comparison artifacts.  
**Required skills:** `add-observability`, `write-tests`, `verify-checkpoint`.  
**Depends on:** Phase 8 checkpoint.

- [ ] **Task 9.1 — Implement standard view rendering**
  - File:

    ```text
    src/visualization/render_views.py
    ```

  - Function:

    ```python
    render_views(stl_path: Path, output_dir: Path, force: bool = False) -> dict
    ```

  - Required outputs:

    ```text
    front.png
    side.png
    top.png
    iso.png
    ```

  - Test file:

    ```text
    tests/test_rendering.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_rendering.py -q
    ```

- [ ] **Task 9.2 — Implement side-by-side comparison**
  - File:

    ```text
    src/visualization/compare_views.py
    ```

  - Function:

    ```python
    build_side_by_side_comparison(original_views_dir: Path, fea_views_dir: Path, output_path: Path, force: bool = False) -> Path
    ```

  - Output:

    ```text
    03_comparison/side_by_side.png
    ```

  - Test file:

    ```text
    tests/test_rendering.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_rendering.py -q
    ```

- [ ] **Task 9.3 — Implement markdown comparison reports**
  - File:

    ```text
    src/reports/build_comparison_report.py
    ```

  - Function:

    ```python
    build_comparison_artifacts(original_prompt: str, fea_prompt: str, output_dir: Path, notes: dict | None = None, force: bool = False) -> dict
    ```

  - Outputs:

    ```text
    03_comparison/prompt_diff.md
    03_comparison/geometry_diff_notes.md
    ```

  - Test file:

    ```text
    tests/test_reports.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_reports.py -q
    ```

### Checkpoint 9

- [ ] Rendering tests pass.
- [ ] Report tests pass.
- [ ] Required PNG and markdown artifacts are created in test temp dirs.
- [ ] `docs/session_state.md` records Phase 9 status.

---

## Phase 10: Manual FreeCAD FEM Artifacts

**Purpose:** prepare manual FreeCAD FEM + CalculiX workflow artifacts.  
**Required skills:** `add-observability`, `write-tests`, `verify-checkpoint`.  
**Depends on:** Phase 9 checkpoint.

- [ ] **Task 10.1 — Implement FreeCAD instructions writer**
  - File:

    ```text
    src/fea/freecad_manual_instructions.py
    ```

  - Function:

    ```python
    write_freecad_instructions(sample_id: str, step_path: Path, load_case: LoadCase, output_path: Path, force: bool = False) -> Path
    ```

  - Output:

    ```text
    04_manual_freecad_fea/freecad_instructions.md
    ```

  - Required content:
    - open FreeCAD,
    - import `fea_ready.step`,
    - switch to FEM workbench,
    - assign Aluminum 6061-T6,
    - apply fixed support,
    - apply 200 N downward force,
    - mesh with Gmsh or Netgen,
    - run CalculiX,
    - save screenshots,
    - record max stress/displacement.
  - Test file:

    ```text
    tests/test_freecad_manual.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_freecad_manual.py -q
    ```

- [ ] **Task 10.2 — Implement manual FEA report template**
  - File:

    ```text
    src/fea/manual_report.py
    ```

  - Function:

    ```python
    write_manual_fea_report_template(sample_id: str, output_path: Path, force: bool = False) -> ManualFEAReport
    ```

  - Output:

    ```text
    04_manual_freecad_fea/fea_report.json
    ```

  - Test file:

    ```text
    tests/test_manual_fea_report.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_manual_fea_report.py -q
    ```

- [ ] **Task 10.3 — Implement post-FEA prompt and final comparison template**
  - Files:

    ```text
    src/fea/post_fea_prompt.py
    src/reports/build_comparison_report.py
    ```

  - Function:

    ```python
    write_post_fea_prompt(sample_id: str, load_case: LoadCase, report_path: Path, output_dir: Path, force: bool = False) -> dict
    ```

  - Outputs:

    ```text
    05_post_fea_refinement/fea_feedback_prompt.txt
    05_post_fea_refinement/comparison_after_fea.md
    ```

  - Test files:

    ```text
    tests/test_manual_fea_report.py
    tests/test_reports.py
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_manual_fea_report.py tests/test_reports.py -q
    ```

### Checkpoint 10

- [ ] FreeCAD manual tests pass.
- [ ] Manual FEA report tests pass.
- [ ] Artifact templates include required manual workflow text.
- [ ] `docs/session_state.md` records Phase 10 status.

---

## Phase 11: CLI And Full Pipeline

**Purpose:** expose the complete workflow through CLI and thin runners.  
**Required skills:** `design-runner`, `add-observability`, `write-tests`, `verify-checkpoint`.  
**Depends on:** Phase 10 checkpoint.

- [ ] **Task 11.1 — Implement public runners**
  - File:

    ```text
    src/runners.py
    ```

  - Functions:

    ```python
    inspect_schema_runner(config_name: str) -> dict
    run_full_pipeline_runner(config_name: str, sample_id: str | None, random: bool, expert_random: bool, force: bool) -> PipelineSummary
    render_only_runner(config_name: str, sample_id: str, force: bool) -> dict
    build_fea_prompt_only_runner(config_name: str, sample_id: str, force: bool) -> dict
    build_freecad_instructions_only_runner(config_name: str, sample_id: str, force: bool) -> dict
    compare_only_runner(config_name: str, sample_id: str, force: bool) -> dict
    ```

  - Rule: runners call stage functions only.
  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_cli.py -q
    ```

- [ ] **Task 11.2 — Implement public interfaces module**
  - File:

    ```text
    src/interfaces.py
    ```

  - Behavior:
    - Re-export schema types and stable public functions only.
    - Provide the import surface used by tests and notebook code.
    - Keep tests and notebooks from importing deep internal modules directly.
  - Required exports:

    ```python
    CADSample
    PipelineConfig
    LoadCase
    ManualFEAReport
    PipelineSummary
    inspect_schema
    load_sample
    generate_original_code
    execute_and_export_cadquery
    build_fea_prompt
    write_load_case
    generate_fea_ready_code
    render_views
    build_comparison_artifacts
    write_freecad_instructions
    write_manual_fea_report_template
    write_post_fea_prompt
    run_full_pipeline
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_interfaces.py -q
    ```

- [ ] **Task 11.3 — Implement run manifest writer**
  - Files:

    ```text
    src/orchestration/manifest.py
    src/schemas/pipeline.py
    ```

  - Behavior:
    - Write `outputs/sample_<sample_id>/run_manifest.json`.
    - Record sample ID, selected config, stage statuses, artifact paths, and failures.
    - Update the manifest incrementally as the pipeline progresses.
  - Required top-level keys:

    ```text
    sample_id
    config_name
    output_dir
    started_at
    finished_at
    stage_statuses
    artifact_paths
    failures
    ```

  - Allowed stage status values:

    ```text
    pending
    running
    passed
    failed
    skipped
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_run_manifest.py -q
    ```

- [ ] **Task 11.4 — Implement pipeline orchestration**
  - File:

    ```text
    src/orchestration/pipeline.py
    ```

  - Function:

    ```python
    run_full_pipeline(config: PipelineConfig, selection: dict) -> PipelineSummary
    ```

  - Rule: no business logic in orchestration; only stage calls and manifest updates.
  - Rule: call stages in the exact order defined in `02-basic-sample-fea-architecture.md`.
  - `selection` keys:

    ```text
    sample_id
    random
    expert_random
    ```

  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests/test_cli.py -q
    ```

- [ ] **Task 11.5 — Implement CLI**
  - File:

    ```text
    src/main.py
    ```

  - Commands:

    ```text
    inspect-schema
    run
    render-only
    build-fea-prompt
    build-freecad-instructions
    compare
    ```

  - Required options:

    ```text
    --config
    --force
    --sample-id
    --random
    --expert-random
    ```

  - Behavior:
    - `run` must reject zero selection flags and multiple selection flags.
    - `render-only`, `build-fea-prompt`, `build-freecad-instructions`, and `compare` must require `--sample-id`.
    - `inspect-schema` must reject sample-selection flags.
  - Verify:

    ```bash
    cd code_base/fea_cad_one_sample
    /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m src.main --help
    ```

### Checkpoint 11

- [ ] CLI tests pass.
- [ ] Interface import tests pass.
- [ ] Run manifest tests pass.
- [ ] `python -m src.main --help` exits 0.
- [ ] `--force` is accepted by relevant write commands.
- [ ] `run_manifest.json` is written with stage statuses and artifact paths.
- [ ] With env vars set, `run --expert-random` creates a full sample output workspace.
- [ ] `docs/session_state.md` records Phase 11 status.

---

## Phase 12: Notebook And Documentation

**Purpose:** finish inspection surfaces and keep agent context current.  
**Required skills:** `design-feature-notebook`, `write-module-readme`, `update-codebase-map`, `update-system-diagram`, `update-docs`, `verify-checkpoint`, `handoff-coding-agent`.  
**Depends on:** Phase 11 checkpoint.

- [ ] **Task 12.1 — Create inspection notebook**
  - File:

    ```text
    notebooks/one_sample_fea_inspection.ipynb
    ```

  - Requirements:
    - Calls public entry points only.
    - Includes setup, test input, public entry check, stage inspection, assertions, failure case, artifact inspection, debugging notes, and summary.
  - Verify:

    ```bash
    test -s code_base/fea_cad_one_sample/notebooks/one_sample_fea_inspection.ipynb
    ```

- [ ] **Task 12.2 — Update module README**
  - File:

    ```text
    code_base/fea_cad_one_sample/README.md
    ```

  - Include current entry points, run commands, internal structure, and Mermaid layer diagram.
  - Verify:

    ```bash
    rg -n "flowchart TD|python -m src.main|interfaces.py|runners.py" code_base/fea_cad_one_sample/README.md
    ```

- [ ] **Task 12.3 — Update agent maps**
  - Files:

    ```text
    docs/ai_context/DOC_TAXONOMY.md
    docs/ai_context/CODEBASE_MAP.md
    docs/ai_context/SYSTEM_WORKFLOW_MAP.md
    ```

  - Verify:

    ```bash
    rg -n "Documentation Authority Order|Documentation Verification Rules|Main Intent Guardrails" docs/ai_context/DOC_TAXONOMY.md
    rg -n "fea_cad_one_sample|run_full_pipeline|CADSample|LoadCase" docs/ai_context/CODEBASE_MAP.md
    rg -n "Load expert prompt|Generate baseline|FreeCAD" docs/ai_context/SYSTEM_WORKFLOW_MAP.md
    ```

- [ ] **Task 12.4 — Final tracking update**
  - File:

    ```text
    docs/session_state.md
    ```

  - Record final checkpoint status and completed phases.
  - Verify:

    ```bash
    rg -n "Final checkpoint|Complete|Phase 12" docs/session_state.md
    ```

### Final Checkpoint

- [ ] Full tests pass:

  ```bash
  cd code_base/fea_cad_one_sample
  /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m pytest tests -q
  ```

- [ ] Compile check passes:

  ```bash
  /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m compileall code_base/fea_cad_one_sample
  ```

- [ ] Full pipeline command creates required workspace:

  ```bash
  cd code_base/fea_cad_one_sample
  /opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python -m src.main run --expert-random --config config_gpt_5_4_mini.yaml
  ```

- [ ] Docs reflect actual code.
- [ ] Documentation verification commands in `docs/ai_context/DOC_TAXONOMY.md` pass.
- [ ] `docs/session_state.md` records completion.
