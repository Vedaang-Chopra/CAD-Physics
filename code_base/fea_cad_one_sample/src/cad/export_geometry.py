"""Export CadQuery geometry to STEP and STL artifacts."""

# pyright: reportMissingImports=false

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def export_step_and_stl(cad_object: Any, output_dir: Path, basename: str, force: bool = False) -> dict[str, str]:
    """Export a CadQuery object to STEP and STL files in the given directory."""

    logger.info(
        "export_step_and_stl | start | output_dir=%s | basename=%s | force=%s",
        output_dir,
        basename,
        force,
    )
    try:
        export_dir = Path(output_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        step_path = export_dir / f"{basename}.step"
        stl_path = export_dir / f"{basename}.stl"

        if not force and (step_path.exists() or stl_path.exists()):
            raise FileExistsError(f"Refusing to overwrite existing exports in {export_dir}.")

        _export_with_cadquery(cad_object, step_path)
        _export_with_cadquery(cad_object, stl_path)
        result = {"step_path": str(step_path), "stl_path": str(stl_path)}
        logger.info("export_step_and_stl | done | step_path=%s | stl_path=%s", step_path, stl_path)
        return result
    except Exception:
        logger.exception(
            "export_step_and_stl | failed | output_dir=%s | basename=%s | force=%s",
            output_dir,
            basename,
            force,
        )
        raise


def _export_with_cadquery(cad_object: Any, output_path: Path) -> None:
    """Write one export using CadQuery's exporters."""

    import cadquery as cq

    cq.exporters.export(cad_object, str(output_path))
