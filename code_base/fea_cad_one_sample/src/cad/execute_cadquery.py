"""Execute CadQuery scripts and export the resulting geometry."""

from __future__ import annotations

import contextlib
import io
import logging
import os
import shutil
import tempfile
from importlib import import_module
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def execute_and_export_cadquery(
    code: str,
    output_dir: Path,
    basename: str,
    force: bool = False,
) -> dict[str, Any]:
    """Execute CadQuery code and export STEP/STL artifacts."""

    logger.info(
        "execute_and_export_cadquery | start | output_dir=%s | basename=%s | force=%s",
        output_dir,
        basename,
        force,
    )
    output_dir = Path(output_dir)
    step_path = output_dir / f"{basename}.step"
    stl_path = output_dir / f"{basename}.stl"
    log_path = output_dir / "execution_log.txt"
    has_existing_outputs = _has_existing_outputs(step_path, stl_path, log_path)

    try:
        _ensure_can_write_outputs(step_path, stl_path, log_path, force=force)
        output_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix=f"{basename}_exec_", dir=str(output_dir.parent)) as temp_root:
            temp_root_path = Path(temp_root)
            script_path = temp_root_path / f"{basename}.py"
            script_path.write_text(code, encoding="utf-8")
            execution = _run_code_in_isolation(code, script_path, temp_root_path)
            export_temp_dir = temp_root_path / "exports"
            export_step_and_stl = _load_export_step_and_stl()
            export_info = export_step_and_stl(
                execution["cad_object"],
                export_temp_dir,
                basename,
                force=True,
            )

            temp_step = Path(export_info["step_path"])
            temp_stl = Path(export_info["stl_path"])
            if force:
                _remove_existing_outputs(step_path, stl_path, log_path)
            shutil.move(str(temp_step), str(step_path))
            shutil.move(str(temp_stl), str(stl_path))

            log_text = _format_execution_log(
                code_path=script_path,
                stdout=execution["stdout"],
                stderr=execution["stderr"],
                candidate_name=execution["candidate_name"],
                candidate_type=execution["candidate_type"],
                step_path=step_path,
                stl_path=stl_path,
                status="success",
            )
            log_path.write_text(log_text, encoding="utf-8")
            result = {
                "success": True,
                "candidate_name": execution["candidate_name"],
                "candidate_type": execution["candidate_type"],
                "script_path": str(script_path),
                "step_path": str(step_path),
                "stl_path": str(stl_path),
                "execution_log_path": str(log_path),
                "stdout": execution["stdout"],
                "stderr": execution["stderr"],
            }
            logger.info(
                "execute_and_export_cadquery | done | step_path=%s | stl_path=%s",
                step_path,
                stl_path,
            )
            return result
    except Exception as exc:
        if force or not has_existing_outputs:
            output_dir.mkdir(parents=True, exist_ok=True)
            log_text = _format_execution_log(
                code_path=output_dir / f"{basename}.py",
                stdout=getattr(exc, "stdout", ""),
                stderr=str(exc),
                candidate_name=None,
                candidate_type=None,
                step_path=step_path,
                stl_path=stl_path,
                status="failure",
            )
            log_path.write_text(log_text, encoding="utf-8")
        logger.exception(
            "execute_and_export_cadquery | failed | output_dir=%s | basename=%s | force=%s",
            output_dir,
            basename,
            force,
        )
        raise


def _load_export_step_and_stl():
    """Load the export helper lazily to avoid import-time dependency issues."""

    module = import_module("src.cad.export_geometry")
    return module.export_step_and_stl


def _ensure_can_write_outputs(step_path: Path, stl_path: Path, log_path: Path, *, force: bool) -> None:
    """Reject overwrite attempts unless force is enabled."""

    if force:
        return
    if any(path.exists() for path in (step_path, stl_path, log_path)):
        raise FileExistsError(f"Existing outputs found for {step_path.stem}. Use force=True to overwrite.")


def _has_existing_outputs(step_path: Path, stl_path: Path, log_path: Path) -> bool:
    """Return whether any baseline output already exists."""

    return any(path.exists() for path in (step_path, stl_path, log_path))


def _remove_existing_outputs(step_path: Path, stl_path: Path, log_path: Path) -> None:
    """Remove existing exported files before overwriting."""

    for path in (step_path, stl_path, log_path):
        if path.exists():
            path.unlink()


def _run_code_in_isolation(code: str, script_path: Path, working_dir: Path) -> dict[str, Any]:
    """Execute code in a clean namespace and recover the CadQuery object."""

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    namespace: dict[str, Any] = {"__name__": "__main__"}
    cwd = Path.cwd()
    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            os.chdir(working_dir)
            exec(compile(code, str(script_path), "exec"), namespace, namespace)
    finally:
        os.chdir(cwd)

    candidate_name, cad_object = _find_cadquery_object(namespace)
    return {
        "stdout": stdout_buffer.getvalue(),
        "stderr": stderr_buffer.getvalue(),
        "candidate_name": candidate_name,
        "candidate_type": type(cad_object).__name__,
        "cad_object": cad_object,
    }


def _find_cadquery_object(namespace: dict[str, Any]) -> tuple[str | None, Any]:
    """Find ``result`` or the last exportable CadQuery object in a namespace."""

    if "result" in namespace and _is_cadquery_object(namespace["result"]):
        return "result", namespace["result"]

    for name, value in reversed(list(namespace.items())):
        if name.startswith("__"):
            continue
        if _is_cadquery_object(value):
            return name, value

    raise ValueError("No CadQuery object named result or similar was produced by the code.")


def _is_cadquery_object(value: Any) -> bool:
    """Heuristically detect CadQuery exportable objects."""

    module_name = getattr(type(value), "__module__", "") or ""
    if module_name.startswith("cadquery"):
        return True
    return any(hasattr(value, attr) for attr in ("wrapped", "exportStep", "val"))


def _format_execution_log(
    *,
    code_path: Path,
    stdout: str,
    stderr: str,
    candidate_name: str | None,
    candidate_type: str | None,
    step_path: Path,
    stl_path: Path,
    status: str,
) -> str:
    """Format a plain-text execution log."""

    lines = [
        f"status: {status}",
        f"code_path: {code_path}",
        f"candidate_name: {candidate_name or '-'}",
        f"candidate_type: {candidate_type or '-'}",
        f"step_path: {step_path}",
        f"stl_path: {stl_path}",
        "",
        "stdout:",
        stdout.strip() or "<empty>",
        "",
        "stderr:",
        stderr.strip() or "<empty>",
    ]
    return "\n".join(lines).rstrip() + "\n"
