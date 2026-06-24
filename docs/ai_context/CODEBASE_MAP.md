# CODEBASE_MAP.md

> Agent-facing map for CAD-Physics. Update this file whenever module structure, public APIs, or ownership changes.

## Current State

CAD-Physics now has a created `code_base/fea_cad_one_sample/` module skeleton with README, packaging files, and the `src/` directory layout. Production behavior is still pending in later phases, but the ownership boundaries are now fixed.

The main intent is captured in `conversations/01-start.md`: move CADCodeVerify from geometry-only CAD toward physics-aware CAD by preparing a STEP-first, manual-FEA-ready workflow with structured load cases and feedback artifacts.

## Module Dependency Diagram

```mermaid
graph TD
    notebook[notebooks/] --> iface[src/interfaces.py]
    cli[src/main.py] --> runners[src/runners.py]
    iface --> runners
    runners --> pipeline[src/orchestration/pipeline.py]
    pipeline --> db[src/db/]
    pipeline --> cad[src/cad/]
    pipeline --> prompts[src/prompts/]
    pipeline --> viz[src/visualization/]
    pipeline --> fea[src/fea/]
    pipeline --> reports[src/reports/]
    db --> schemas[src/schemas/]
    cad --> schemas
    prompts --> schemas
    fea --> schemas
    reports --> schemas
    db --> copied[src/copied_from_cadcodeverify/]
    cad --> copied
    viz --> copied
```

## Top-Level Directory Structure

```text
CAD-Physics/
  code_base/
    fea_cad_one_sample/
      README.md
      pyproject.toml
      requirements.txt
      notebooks/
      outputs/
      src/
      tests/
  conversations/
  docs/
    ai_context/
      DOC_TAXONOMY.md
      CODEBASE_MAP.md
      SYSTEM_WORKFLOW_MAP.md
    execution-plans/
    gpt-specs/
```

## Module Ownership

| Module | Purpose | Owns | Does NOT Own |
|---|---|---|---|
| `code_base/fea_cad_one_sample/` | One-sample CAD prompt to FEA-ready CAD workflow | Module-local orchestration, sample loading, CAD execution/export, rendering, FEA artifacts, copied reference helpers | Multi-sample benchmarks, automated FEA, training, CAD Design runtime package ownership |
| `docs/execution-plans/` | Pi execution instructions | Protocol, local spec, architecture, microtasks, checkpoints, handoff template | Runtime code |
| `docs/execution-plans/06-pi-sequential-execution-prompt.md` | Pi execution launcher | Sequential task-loop prompt, context-stop behavior, final acceptance reminders | Source code |
| `docs/ai_context/` | Agent orientation maps | Documentation taxonomy, codebase map, and workflow map | Feature requirements |

## Public Entry Points

| Module | File | Public Functions |
|---|---|---|
| `fea_cad_one_sample` | `src/interfaces.py` | placeholder public API surface |
| `fea_cad_one_sample` | `src/runners.py` | placeholder runner surface |
| `fea_cad_one_sample` | `src/main.py` | placeholder CLI entry point |

## Schemas And Data Contracts

| Schema | Location | Used By |
|---|---|---|
| `CADSample` | `src/schemas/sample.py` | DB loader, generation, prompt builder |
| `PipelineConfig` | `src/schemas/config.py` | CLI, runners, pipeline |
| `LoadCase` | `src/schemas/fea.py` | FEA prompt, load-case writer, FreeCAD docs |
| `ManualFEAReport` | `src/schemas/fea.py` | manual report writer, post-FEA prompt |
| `PipelineSummary` | `src/schemas/pipeline.py` | pipeline, CLI output, manifest |
| `RunManifestRecord` | `src/schemas/pipeline.py` | manifest writer and stage tracking |

## What Not To Duplicate

- Do not reimplement copied CAD Design helpers in multiple local modules.
- Do not put production logic in notebooks.
- Do not put business logic in `src/main.py`, `src/runners.py`, or `src/orchestration/pipeline.py`.
- Do not import from CAD Design in production code unless the user approves a spec change.
- Do not automate FreeCAD or CalculiX in this first prototype.

## Module Inventory

| Module | Public Files | Notes |
|---|---|---|
| `fea_cad_one_sample` | `interfaces.py`, `runners.py`, `main.py` | Skeleton in place; functional APIs pending Phase 5+ |
| `fea_cad_one_sample` | `schemas/`, `orchestration/`, `db/`, `cad/`, `prompts/`, `visualization/`, `fea/`, `reports/`, `copied_from_cadcodeverify/` | Directory ownership established |

## Known Gaps / Technical Debt

- Production logic is not implemented yet.
- DB and model environment variables will be required in later phases.
- Real DB schema must be inspected before assuming expert-prompt field names.
- `cad_physics` exists now; the old gap note is resolved.

## Changelog

| Date | Change |
|---|---|
| 2026-06-24 | Marked `fea_cad_one_sample` skeleton as created and updated ownership tables. |
| 2026-06-24 | Added documentation taxonomy, sequential Pi prompt ownership, and main-intent guardrail. |
| 2026-06-24 | Created initial map for planned one-sample FEA-ready CAD prototype. |
