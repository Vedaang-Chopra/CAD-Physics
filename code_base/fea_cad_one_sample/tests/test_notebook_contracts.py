"""Contract tests for the notebook walkthrough."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

NOTEBOOK_DIR = Path("notebooks")
EXPECTED_NOTEBOOKS = {
    "00_select_real_sample.ipynb",
    "01_state_a_dataset_original.ipynb",
    "02_state_b_fea_revision.ipynb",
    "03_manual_freecad_fea_handoff.ipynb",
    "04_state_c_post_fea_revision.ipynb",
    "05_final_abc_comparison.ipynb",
    "one_sample_fea_inspection.ipynb",
}
ALLOWED_PUBLIC_IMPORTS = {"src.interfaces", "src.runners"}
FORBIDDEN_PATTERNS = (
    "sample_box",
    "02_fea_ready",
    "05_post_fea_refinement",
    "tempfile.mkdtemp",
    "postgresql://",
    "sqlite:///",
    "vlmrouter",
    "password=",
)
PUBLIC_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(src(?:\.[A-Za-z_][\w.]*)?)", re.MULTILINE)


def _load_notebook(path: Path) -> dict:
    """Load a notebook JSON document."""

    return json.loads(path.read_text(encoding="utf-8"))


def _cell_source(cell: dict) -> str:
    """Normalize a notebook cell source to a single string."""

    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(source)
    return str(source)


def test_notebook_inventory_and_outputs_are_cleared() -> None:
    """The walkthrough notebook set exists and has cleared execution state."""

    assert NOTEBOOK_DIR.is_dir()
    notebook_names = {path.name for path in NOTEBOOK_DIR.glob("*.ipynb")}
    assert EXPECTED_NOTEBOOKS.issubset(notebook_names)

    for path in sorted(NOTEBOOK_DIR.glob("*.ipynb")):
        notebook = _load_notebook(path)
        assert notebook["nbformat"] == 4
        assert notebook["nbformat_minor"] >= 5
        for cell in notebook.get("cells", []):
            source = _cell_source(cell)
            if cell.get("cell_type") == "code":
                assert cell.get("execution_count") is None, f"{path.name} has stale execution count"
                assert cell.get("outputs") == [], f"{path.name} has stale outputs"
            assert "sample_box" not in source, f"synthetic sample_box reference found in {path.name}"


def test_notebooks_use_only_public_interfaces() -> None:
    """Notebook imports stay on the public `src.interfaces`/`src.runners` surface."""

    for path in sorted(NOTEBOOK_DIR.glob("*.ipynb")):
        notebook = _load_notebook(path)
        sources = [_cell_source(cell) for cell in notebook.get("cells", [])]
        text = "\n".join(sources)

        found_modules = set(PUBLIC_IMPORT_RE.findall(text))
        disallowed = sorted(module for module in found_modules if module not in ALLOWED_PUBLIC_IMPORTS)
        assert not disallowed, f"{path.name} imports non-public src modules: {disallowed}"

        assert "tempfile.mkdtemp" not in text, f"{path.name} should not use a synthetic temp workspace"
        assert "02_fea_ready" not in text, f"{path.name} still references the old FEA-ready output tree"
        assert "05_post_fea_refinement" not in text, f"{path.name} still references the old post-FEA output tree"

        if path.name != "one_sample_fea_inspection.ipynb":
            assert "sample-001" in text or "sample_{sample_id}" in text or "sample_sample-001" in text, (
                f"{path.name} should reference the real sample tree"
            )

        for pattern in FORBIDDEN_PATTERNS[3:]:
            assert pattern not in text, f"{path.name} contains forbidden pattern: {pattern}"


@pytest.mark.parametrize(
    "path_name, expected_text",
    [
        ("00_select_real_sample.ipynb", "sample_{sample_id}"),
        ("01_state_a_dataset_original.ipynb", "sample_{sample_id}"),
        ("02_state_b_fea_revision.ipynb", "sample_{sample_id}"),
        ("03_manual_freecad_fea_handoff.ipynb", "sample_{sample_id}"),
        ("04_state_c_post_fea_revision.ipynb", "sample_{sample_id}"),
        ("05_final_abc_comparison.ipynb", "sample_{sample_id}"),
        ("one_sample_fea_inspection.ipynb", "sample_{sample_id}"),
    ],
)
def test_notebooks_reference_real_artifact_roots(path_name: str, expected_text: str) -> None:
    """Each notebook points at the canonical real artifact tree."""

    notebook = _load_notebook(NOTEBOOK_DIR / path_name)
    text = "\n".join(_cell_source(cell) for cell in notebook.get("cells", []))
    assert expected_text in text
