# Remediation Architecture: Related-State CAD-Physics Experiment

## Summary

The corrected architecture keeps the existing layered module shape but changes the experiment ownership. The module must stop treating the baseline as a generated artifact and instead make DB-original State A the immutable root of the experiment. State B and State C become revisions of earlier states, not independent generations.

## Layer Plan

| Layer | Ownership | Remediation responsibility |
|---|---|---|
| Layer 1 - Notebooks | `code_base/fea_cad_one_sample/notebooks/` | Real multi-notebook walkthrough over `outputs/sample_<sample_id>/`; public imports only |
| Layer 2 - Public Interface | `src/interfaces.py`, `src/runners.py`, `src/main.py` | Expose stable State A/B/C runner contracts and CLI commands |
| Layer 3 - Orchestration | `src/orchestration/pipeline.py`, `src/orchestration/manifest.py` | Order State A, State B, manual FEA preparation, gated State C, comparison |
| Layer 4 - Core | `src/db/`, `src/cad/`, `src/prompts/`, `src/fea/`, `src/visualization/`, `src/reports/` | Implement loading, revisions, execution/export, manual gate, visualization, metrics |
| Layer 5 - Schemas / Utilities | `src/schemas/`, local wrappers around copied helpers | Define result contracts, provenance, change logs, geometry metrics, selector hints |

## Proposed Public Contracts

State A:

```python
def load_dataset_original_sample(
    connection_string: str,
    sample_id: str | None = None,
    random: bool = False,
    expert_random: bool = False,
) -> CADSample:
    ...

def persist_dataset_original_state(
    sample: CADSample,
    output_dir: Path,
    force: bool = False,
) -> DatasetOriginalResult:
    ...
```

State B:

```python
def revise_code_for_fea(
    original_prompt: str,
    original_code: str,
    load_case: LoadCase,
    selector_hints: dict,
    config: PipelineConfig,
) -> FEARevisionResult:
    ...
```

State C:

```python
def revise_code_after_fea(
    fea_revision_code: str,
    load_case: LoadCase,
    fea_report: ManualFEAReport,
    screenshots: list[Path],
    config: PipelineConfig,
) -> PostFEARevisionResult:
    ...
```

Comparison:

```python
def render_state_views(
    stl_path: Path,
    output_dir: Path,
    state_label: str,
    force: bool = False,
) -> dict[str, str]:
    ...

def build_three_state_visual_comparison(
    state_a_views: Path,
    state_b_views: Path,
    state_c_views: Path,
    output_path: Path,
    force: bool = False,
) -> Path:
    ...

def compute_geometry_metrics(
    state_paths: dict[str, Path],
    output_path: Path,
    force: bool = False,
) -> GeometryComparisonResult:
    ...
```

## Schema Additions

Add dataclass schemas in `src/schemas/`:

- `DatasetOriginalResult`
  - sample ID, prompt path, DB code path, code hash, provenance path, STEP/STL paths, view paths.
- `FEARevisionResult`
  - prompt path, selector hints path, code path, change log path, provenance path, STEP/STL paths, view paths.
- `PostFEARevisionResult`
  - prompt path, code path, change log path, provenance path, STEP/STL paths, view paths, manual report path.
- `GeometryComparisonResult`
  - per-state metrics, pairwise deltas, output JSON/markdown paths.
- `RevisionChangeLog`
  - changed feature, change type, reason, expected physical effect, original-design identity note.
- `SelectorHints`
  - fixed region description/selector and load region description/selector.

Use simple dataclasses to match the existing project style.

## Pipeline Order

Corrected orchestration order:

```text
1. Resolve config and output directory.
2. Inspect schema when requested or needed.
3. Load DB original sample with prompt and original code.
4. Persist State A original prompt, DB code, metadata, provenance, and hash.
5. Execute/export State A STEP/STL.
6. Render State A views and grid.
7. Build load_case.json and selector_hints.json.
8. Build State B revision prompt from original prompt + original code + load case + selector hints.
9. Generate State B revision code and change log.
10. Execute/export State B STEP/STL.
11. Render State B views, grid, and annotated support/load image.
12. Build A/B comparison artifacts and manual FreeCAD FEM instructions.
13. Stop or mark State C blocked until completed manual FEA results exist.
14. Validate manual FEA report and screenshots/result files.
15. Build State C post-FEA prompt from State B code + actual FEA values.
16. Generate State C code and change log.
17. Execute/export State C STEP/STL.
18. Render State C views and grid.
19. Build A/B/C visual comparison and deterministic geometry metrics.
20. Update run_manifest.json and print summary.
```

## Manual FEA Gate

The pipeline may prepare manual FEA artifacts before the user runs FreeCAD FEM + CalculiX. It must not claim State C complete until all required manual evidence exists.

Required values in `fea_report.json`:

- `max_von_mises_pa`
- `max_displacement_mm`
- `computed_safety_factor`
- `passes_stress`
- `passes_displacement`
- `overall_pass`
- `stress_hotspot_description`

Required files under `04_manual_freecad_fea/`:

- `mesh.png`
- `fixed_region.png`
- `load_region.png`
- `von_mises.png`
- `displacement.png`

If any value is null or any required file is missing, State C must produce a clear blocked status in `run_manifest.json` and must not call the LLM.

## Standalone Copied-Code Policy

Production code must not import old CAD Design modules at runtime. Copied code may remain under `src/copied_from_cadcodeverify/`, but project-specific runtime wrappers must import local copied modules directly.

Current risk to fix:

- `src/copied_from_cadcodeverify/db/connections.py` falls back to `ensure_code_base_on_path()` and imports `utils.llm.llm`.
- The remediation must route LLM creation through local copied `src/copied_from_cadcodeverify/llm/llm.py` or a local wrapper.

## Notebook Architecture

Replace the single synthetic-box notebook proof with a real multi-notebook walkthrough:

```text
notebooks/
  00_select_real_sample.ipynb
  01_state_a_dataset_original.ipynb
  02_state_b_fea_revision.ipynb
  03_manual_fea_handoff.ipynb
  04_state_c_post_fea_revision.ipynb
  05_final_abc_comparison.ipynb
```

Notebook rules:

- Import only from `src.interfaces` or `src.runners`.
- No reusable production logic inside notebook cells.
- No hardcoded DB credentials.
- No synthetic CadQuery box as main evidence.
- Every notebook prints stage inputs, outputs, assertions, artifact paths, and failure/debug notes.
- Notebooks should be executable independently after prior artifacts exist.

## CLI Shape

Retain the existing CLI where possible, but add explicit stage commands:

```bash
python -m src.main run-state-a --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
python -m src.main run-state-b --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
python -m src.main prepare-manual-fea --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
python -m src.main run-state-c --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
python -m src.main compare-abc --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
python -m src.main run --sample-id SAMPLE_ID --config config_gpt_5_4_mini.yaml
```

The full `run` command may stop with State C blocked if manual FEA results are not complete. That is a correct intermediate result, not a completed experiment.

## Documentation Updates Required With Implementation

When implementing this architecture, update these docs in the same change set:

- `docs/ai_context/DOC_TAXONOMY.md`
- `docs/ai_context/CODEBASE_MAP.md`
- `docs/ai_context/SYSTEM_WORKFLOW_MAP.md`
- `docs/session_state.md`
- `code_base/fea_cad_one_sample/README.md`
- existing `docs/execution-plans/` files or new approved equivalents

