# Feature Specification: One-Sample CADCodeVerify to FEA-Ready CAD Pipeline

## 1. Goal

Build a new standalone project that takes one CADCodeVerify/CADPrompt dataset sample, loads its original prompt and generated CadQuery code, visualizes the original geometry, converts the prompt into an FEA-ready engineering prompt, generates or modifies CAD code accordingly, visualizes the FEA-ready geometry, and prepares files for manual FreeCAD FEM + CalculiX validation on macOS.

This is a one-sample prototype. Do not build a full benchmark yet.

The purpose is to understand the difference between:

1. Geometry-only CAD generation.
2. FEA-ready CAD generation.
3. Post-FEA design refinement based on stress/displacement feedback.

## 2. Important Project Constraint

This is a new project.

When reusing code from the existing CADCodeVerify/CAD code project, do not import it as a package dependency.

Instead:

* Copy the needed functions/classes exactly into this new project.
* Preserve the original function behavior.
* Add a short comment above copied code identifying its source file path from the original project.
* Avoid modifying copied code unless necessary.
* If modification is required, create a wrapper around the copied function rather than editing the copied logic directly.

Example:

```python
# Copied exactly from CADCodeVerify: path/to/original/file.py
def render_cad_views(...):
    ...
```

## 3. Representation Choice

Use CadQuery Python as the primary CAD representation.

Reason:

* CADCodeVerify-style generation already works with code-based CAD.
* CadQuery can export STEP, which is suitable for FreeCAD and FEA workflows.
* CadQuery scripts are editable and easy to regenerate.
* STEP is the handoff format for FreeCAD FEM + CalculiX.
* STL may be exported only for visualization or mesh preview, not as the primary engineering CAD format.

The pipeline should preserve:

```text
Prompt → CadQuery code → STEP geometry → visualization → FEA metadata → FreeCAD FEM manual validation
```

## 4. Scope

### In scope

* Load one sample from the existing DB.
* Support sample selection by:

  * explicit sample ID,
  * random sample,
  * first available expert prompt sample.
* Extract the original prompt and original CadQuery code from DB.
* Execute the original CadQuery code.
* Export original geometry as STEP and STL.
* Generate visualizations using existing CADCodeVerify visualization code.
* Create an FEA-ready prompt from the original prompt.
* Create a structured FEA metadata JSON file.
* Generate or modify CadQuery code using the FEA-ready prompt.
* Export FEA-ready geometry as STEP and STL.
* Generate side-by-side visualizations.
* Create manual FreeCAD FEM instructions.
* Store manual CalculiX result screenshots and reports.
* Create a comparison report.

### Out of scope

* Fully automated FEA.
* Fully automated CalculiX execution.
* Full benchmark construction.
* Training or fine-tuning.
* Multi-sample evaluation.
* Automatic physical correctness guarantee.
* Complex thermal, fluid, buckling, or nonlinear simulation.

## 5. Expected User Inputs

Codex should expect the user to provide or point to:

1. Existing DB loading code.
2. Existing DB schema or schema inspection logic.
3. Existing CAD generation code.
4. Existing visualization code.
5. Existing sample selection logic.
6. Any model API wrappers used in CADCodeVerify.
7. Local macOS environment details if needed.

Codex should inspect the schema instead of assuming field names.

Likely fields may include:

```text
sample_id
prompt
expert_prompt
generated_code
cad_code
program
category
split
render_path
metadata
```

But Codex must verify actual names from the DB/schema.

## 6. Recommended First Sample

Use an expert prompt if available.

Prefer a geometry that can meaningfully support a load, such as:

* bracket,
* shelf support,
* mounting arm,
* clamp,
* plate with holes,
* cantilever-like object,
* connector,
* support frame.

Avoid for the first sample:

* purely decorative shapes,
* organic shapes,
* toys,
* abstract shapes,
* objects without clear load/support regions,
* extremely complex assemblies.

If random selection returns a poor FEA candidate, log it and choose another sample.

## 7. Directory Structure

Create this structure:

```text
fea_cad_one_sample/
  README.md
  pyproject.toml
  requirements.txt

  src/
    main.py
    config.py

    db/
      load_sample.py
      schema_inspection.py

    copied_from_cadcodeverify/
      README.md
      visualization_utils.py
      generation_utils.py
      cad_execution_utils.py

    cad/
      execute_cadquery.py
      export_geometry.py
      validate_cad_script.py

    prompts/
      build_fea_prompt.py
      prompt_templates.py

    visualization/
      render_views.py
      compare_views.py
      annotate_regions.py

    fea/
      fea_schema.py
      write_load_case.py
      freecad_manual_instructions.py
      parse_manual_results.py

    reports/
      build_comparison_report.py

  data/
    samples/

  outputs/
    sample_<sample_id>/
      01_original/
        original_prompt.txt
        original_code.py
        original.step
        original.stl
        views/
          front.png
          side.png
          top.png
          iso.png

      02_fea_ready/
        fea_ready_prompt.txt
        load_case.json
        fea_ready_code.py
        fea_ready.step
        fea_ready.stl
        views/
          front.png
          side.png
          top.png
          iso.png

      03_comparison/
        side_by_side.png
        geometry_diff_notes.md
        prompt_diff.md

      04_manual_freecad_fea/
        freecad_instructions.md
        freecad_project.FCStd
        mesh.png
        fixed_region.png
        load_region.png
        von_mises.png
        displacement.png
        raw_notes.txt
        fea_report.json

      05_post_fea_refinement/
        fea_feedback_prompt.txt
        refined_code.py
        refined.step
        refined.stl
        views/
        comparison_after_fea.md
```

## 8. Pipeline Overview

Implement the pipeline as explicit stages.

```text
Stage 1: Load one DB sample
Stage 2: Save original prompt and code
Stage 3: Execute original CadQuery code
Stage 4: Export original STEP/STL
Stage 5: Render original geometry
Stage 6: Convert original prompt into FEA-ready prompt
Stage 7: Create load_case.json
Stage 8: Generate or modify CadQuery code for FEA-ready version
Stage 9: Export FEA-ready STEP/STL
Stage 10: Render FEA-ready geometry
Stage 11: Create manual FreeCAD FEM instructions
Stage 12: User runs FreeCAD FEM + CalculiX manually
Stage 13: User saves screenshots and result values
Stage 14: Create fea_report.json
Stage 15: Generate post-FEA refinement prompt
Stage 16: Generate refined CAD code
Stage 17: Compare original vs FEA-ready vs refined
```

## 9. CLI Requirements

Create a CLI entry point.

Example commands:

```bash
python -m src.main run --sample-id SAMPLE_ID
python -m src.main run --random
python -m src.main run --expert-random
python -m src.main inspect-schema
python -m src.main render-only --sample-id SAMPLE_ID
python -m src.main build-fea-prompt --sample-id SAMPLE_ID
python -m src.main build-freecad-instructions --sample-id SAMPLE_ID
python -m src.main compare --sample-id SAMPLE_ID
```

## 10. Stage Details

### Stage 1: Load One Sample from DB

Codex should implement a loader that wraps the user-provided DB loading code.

The loader should return a normalized object:

```python
@dataclass
class CADSample:
    sample_id: str
    prompt: str
    code: str
    source: str | None = None
    metadata: dict | None = None
```

The actual DB schema may differ. Codex must inspect schema and map fields safely.

Selection modes:

```text
--sample-id
--random
--expert-random
```

If expert/non-expert labels exist, prefer expert samples.

### Stage 2: Save Original Inputs

Save:

```text
original_prompt.txt
original_code.py
metadata.json
```

Do not overwrite existing outputs unless `--force` is passed.

### Stage 3: Execute Original CadQuery Code

Execute the loaded CadQuery code in an isolated working directory.

Requirements:

* Capture stdout/stderr.
* Save execution log.
* Detect whether a valid CadQuery object was produced.
* Export STEP and STL if possible.
* Fail gracefully if code is invalid.

Expected outputs:

```text
original.step
original.stl
execution_log.txt
```

### Stage 4: Visualize Original Geometry

Reuse visualization code from CADCodeVerify by copying the required files/functions into:

```text
src/copied_from_cadcodeverify/
```

Render at least:

```text
front.png
side.png
top.png
iso.png
```

If existing project supports more views, expose a `--num-views` option.

The goal is to show what geometry-based CAD generation produces before adding physical constraints.

### Stage 5: Build FEA-Ready Prompt

Create a prompt transformation module.

Input:

```text
original_prompt
optional sample metadata
default FEA assumptions
```

Output:

```text
fea_ready_prompt.txt
load_case.json
```

The FEA-ready prompt must add:

```text
material
Young's modulus
Poisson's ratio
yield strength
fixed/support region
load region
force magnitude
force direction
maximum displacement
required safety factor
meshability requirements
STEP export requirement
single connected solid requirement
```

Default assumptions for first prototype:

```json
{
  "material": "Aluminum 6061-T6",
  "youngs_modulus_pa": 68900000000,
  "poissons_ratio": 0.33,
  "yield_strength_pa": 276000000,
  "load_n": 200,
  "load_direction": [0, 0, -1],
  "max_displacement_mm": 1.0,
  "required_safety_factor": 2.0
}
```

The stress threshold should be:

```text
max_von_mises = yield_strength / required_safety_factor
```

For Aluminum 6061-T6:

```text
276 MPa / 2 = 138 MPa
```

### Stage 6: Load Case JSON Schema

Write `load_case.json`.

Minimum schema:

```json
{
  "sample_id": "...",
  "units": "mm",
  "material": {
    "name": "Aluminum 6061-T6",
    "youngs_modulus_pa": 68900000000,
    "poissons_ratio": 0.33,
    "yield_strength_pa": 276000000
  },
  "boundary_conditions": [
    {
      "id": "fixed_region",
      "type": "fixed_displacement",
      "description": "User-defined or model-inferred fixed support region",
      "selector": null
    }
  ],
  "loads": [
    {
      "id": "load_region",
      "type": "force",
      "magnitude_n": 200,
      "direction": [0, 0, -1],
      "description": "User-defined or model-inferred load application region",
      "selector": null
    }
  ],
  "requirements": {
    "max_displacement_mm": 1.0,
    "required_safety_factor": 2.0,
    "max_von_mises_pa": 138000000
  }
}
```

For the first version, selectors can be text descriptions instead of exact geometric selectors if exact selectors are hard to infer.

Later versions can add bounding-box selectors.

### Stage 7: Generate FEA-Ready CAD Code

Use existing generation logic from the CADCodeVerify project, copied into this project.

The model prompt should instruct:

```text
Generate CadQuery Python code.
Preserve the original design intent.
Make the geometry suitable for FEA.
Use a single connected solid.
Avoid tiny decorative features.
Use clear flat support and load regions.
Export STEP.
Prefer simple mechanical structure.
```

The FEA-ready geometry may differ from the original. This is expected.

Possible changes:

```text
thicker walls
added ribs/gussets
larger support plate
simplified features
removed decorative details
larger fillets
clearer load-bearing path
flat force application face
flat fixed boundary face
```

### Stage 8: Visualize FEA-Ready Geometry

Render the same views as the original geometry.

Save:

```text
02_fea_ready/views/front.png
02_fea_ready/views/side.png
02_fea_ready/views/top.png
02_fea_ready/views/iso.png
```

Also create:

```text
03_comparison/side_by_side.png
03_comparison/prompt_diff.md
03_comparison/geometry_diff_notes.md
```

The comparison should answer:

```text
What changed visually?
Did the object become thicker?
Were ribs/gussets added?
Were load/support regions made clearer?
Was geometry simplified?
Is the object still aligned with the original prompt?
```

### Stage 9: Manual FreeCAD FEM + CalculiX Instructions

Generate a markdown file:

```text
04_manual_freecad_fea/freecad_instructions.md
```

The file should guide the user through macOS FreeCAD FEM manually.

Required steps:

```text
1. Open FreeCAD.
2. Import fea_ready.step.
3. Switch to FEM workbench.
4. Create analysis.
5. Assign material: Aluminum 6061-T6.
6. Set Young's modulus, Poisson's ratio, yield strength.
7. Add fixed constraint to fixed/support face.
8. Add force constraint: 200 N downward on load face.
9. Create mesh using Gmsh or Netgen.
10. Run CalculiX.
11. Open results.
12. Save screenshots:
    - mesh.png
    - fixed_region.png
    - load_region.png
    - von_mises.png
    - displacement.png
13. Record:
    - max von Mises stress
    - max displacement
    - solver success/failure
    - visible stress hotspot location
```

macOS note:

* FreeCAD FEM + CalculiX can be used manually on macOS.
* If FreeCAD does not find CalculiX automatically, the user may need to configure the CalculiX binary path in FreeCAD preferences.
* Do not require automated CalculiX execution in this prototype.

### Stage 10: Manual FEA Report

Create a helper script or template for:

```text
04_manual_freecad_fea/fea_report.json
```

Template:

```json
{
  "sample_id": "...",
  "solver": "FreeCAD FEM + CalculiX",
  "manual_run": true,
  "max_von_mises_pa": null,
  "max_displacement_mm": null,
  "yield_strength_pa": 276000000,
  "required_safety_factor": 2.0,
  "computed_safety_factor": null,
  "passes_stress": null,
  "passes_displacement": null,
  "overall_pass": null,
  "stress_hotspot_description": "",
  "notes": []
}
```

When user enters max stress, compute:

```text
computed_safety_factor = yield_strength / max_von_mises
```

Pass conditions:

```text
passes_stress = computed_safety_factor >= required_safety_factor
passes_displacement = max_displacement_mm <= 1.0
overall_pass = passes_stress and passes_displacement
```

### Stage 11: Post-FEA Refinement Prompt

After manual FEA results are saved, generate:

```text
05_post_fea_refinement/fea_feedback_prompt.txt
```

Template:

```text
The CAD design was tested using FreeCAD FEM + CalculiX.

Original task:
{fea_ready_prompt}

FEA result:
- Max von Mises stress: {max_von_mises}
- Max displacement: {max_displacement}
- Computed safety factor: {computed_safety_factor}
- Stress hotspot: {stress_hotspot_description}
- Pass/fail: {overall_pass}

Revise the CadQuery design.
Keep the original design intent.
Do not change the material or load.
Improve stress and displacement performance.
Prefer simple meshable geometry.
Use one connected solid.
Preserve clear fixed and load regions.
Export STEP.
```

Expected model changes after FEA feedback:

```text
If stress too high:
- add gussets/ribs,
- increase thickness,
- add fillets near hotspot,
- improve load path.

If displacement too high:
- increase section height,
- add triangular support,
- shorten unsupported span if allowed,
- add stiffening rib.

If overbuilt:
- reduce unnecessary bulk,
- add cutouts away from stress paths,
- keep safety factor above requirement.
```

### Stage 12: Final Comparison Report

Generate:

```text
05_post_fea_refinement/comparison_after_fea.md
```

It should compare:

```text
Original CAD
FEA-ready CAD
Post-FEA refined CAD
```

Include:

```text
Prompt differences
Code differences
Visual differences
FEA result summary
What changed because of physics feedback
Whether the object still satisfies original design intent
```

## 11. Required Output Summary

At the end of a run, print:

```text
Sample ID:
Original prompt path:
Original CAD code path:
Original STEP path:
Original render folder:

FEA-ready prompt path:
Load case JSON path:
FEA-ready CAD code path:
FEA-ready STEP path:
FEA-ready render folder:

Manual FreeCAD instructions:
Manual FEA report template:
Comparison report path:
```

## 12. Error Handling

Handle these cases:

```text
DB sample missing prompt
DB sample missing code
CAD code does not execute
CadQuery object not found
STEP export fails
Visualization fails
Model generation fails
FEA-ready code fails
FreeCAD manual result not yet available
```

Each failure should create a readable log file and should not destroy previous outputs.

## 13. Development Plan for Codex

Create a micro-plan before coding.

The micro-plan should include:

1. Inspect available CADCodeVerify code.
2. Identify DB loader code to copy.
3. Identify visualization code to copy.
4. Identify generation code to copy.
5. Create new project skeleton.
6. Implement normalized sample loader.
7. Implement CadQuery execution/export.
8. Implement visualization wrappers.
9. Implement FEA prompt builder.
10. Implement load case JSON writer.
11. Implement FEA-ready generation flow.
12. Implement comparison report.
13. Implement FreeCAD manual instruction generator.
14. Test with one explicit sample ID.
15. Test with one random expert sample.
16. Document how to run.

## 14. Acceptance Criteria

The feature is complete when one command can produce the full sample workspace:

```bash
python -m src.main run --expert-random
```

And the output contains:

```text
original_prompt.txt
original_code.py
original.step
original rendered views
fea_ready_prompt.txt
load_case.json
fea_ready_code.py
fea_ready.step
fea_ready rendered views
side_by_side.png
freecad_instructions.md
fea_report.json template
comparison report
```

Manual FreeCAD FEM validation is considered successful when the user can:

```text
open fea_ready.step in FreeCAD
assign material
apply fixed support
apply 200 N downward force
mesh the part
run CalculiX
save von Mises and displacement screenshots
fill fea_report.json
generate a post-FEA refinement prompt
```

## 15. Key Design Principle

The first prototype should prioritize clarity over automation.

Do not hide the process.

The user should be able to see:

```text
what the original prompt said
what the original geometry looked like
what FEA details were added
what the FEA-ready prompt said
what the FEA-ready geometry looked like
what changed after FEA feedback
why the change happened
```

This prototype is primarily for understanding and demonstration, not production-scale evaluation.
