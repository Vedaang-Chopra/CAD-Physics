# fea_cad_one_sample

## Purpose

One-sample CADCodeVerify-to-FEA workflow that loads a single sample and prepares baseline, FEA-ready, and manual-FEA artifacts.

## What Belongs Here

- Module-specific CLI entry points, orchestration, schemas, DB loading, CAD execution/export, rendering, FEA artifacts, and comparison reports.
- Copied reference helpers preserved under `src/copied_from_cadcodeverify/`.

## What Does NOT Belong Here

- Shared helpers used by multiple modules → project-level `utils/`.
- Production imports from CAD Design → copy into `src/copied_from_cadcodeverify/` instead.
- Notebook-only inspection code → `notebooks/`.

## Layer Diagram

```mermaid
flowchart TD
    N[notebooks/] --> I[src/interfaces.py]
    I --> R[src/runners.py]
    R --> O[src/orchestration/pipeline.py]
    O --> D[src/db/]
    O --> C[src/cad/]
    O --> P[src/prompts/]
    O --> V[src/visualization/]
    O --> F[src/fea/]
    O --> M[src/reports/]
    D --> S[src/schemas/]
    C --> S
    P --> S
    F --> S
    M --> S
```

## Entry Points

| File | Purpose |
|---|---|
| `src/interfaces.py` | Public API surface for tests and notebooks |
| `src/runners.py` | Thin workflow orchestration entry points |
| `src/main.py` | CLI commands |

## How to Run

- **CLI:** `python -m src.main --help`
- **Tests:** `pytest tests -q`

## Internal Structure

| Directory / File | Responsibility |
|---|---|
| `src/schemas/` | Data contracts |
| `src/orchestration/` | Workflow composition |
| `src/db/` | Schema inspection and sample loading |
| `src/cad/` | CadQuery execution and export |
| `src/prompts/` | FEA prompt construction |
| `src/visualization/` | Rendering and comparison images |
| `src/fea/` | Manual FreeCAD FEM instructions, manual report template, and post-FEA prompt artifacts |
| `src/reports/` | Comparison markdown artifacts, including the post-FEA comparison template |
| `src/copied_from_cadcodeverify/` | Local copies of approved reference helpers |
