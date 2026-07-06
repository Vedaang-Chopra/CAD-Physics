# fea_replication

Deterministic STEP → Gmsh mesh → CalculiX pipeline for one beam model.

## Responsibilities

- Create or load a single STEP geometry.
- Render a lightweight Python geometry preview.
- Generate a 3D tetra mesh with Gmsh.
- Select fixed/load node sets near opposite ends of the part.
- Write a CalculiX-compatible `.inp` file.
- Run `ccx` from Python.
- Parse displacement and best-effort stress outputs.
- Run a load-magnitude parametric study.

## Public access

Notebooks should import this package through `src.interfaces` only.

## Default run directory

```text
code_base/fea_cad_one_sample/outputs/fea_replication/baseline/
```

## Notes

- The pipeline uses mm–N–MPa in the CalculiX deck.
- Material values are stored in Pa in the config object and converted when writing the deck.
- Stress parsing is best-effort and marked TODO when the `.dat` block format is not sufficient.
