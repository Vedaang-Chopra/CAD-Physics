"""Run CalculiX from Python and capture solver artifacts."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .schemas import FEAReplicationConfig, MeshSummary, SolverRunSummary
from .utils import write_text

logger = logging.getLogger(__name__)


def run_calculix_solver(config: FEAReplicationConfig, mesh_summary: MeshSummary) -> SolverRunSummary:
    """Execute ccx for one mesh and capture stdout/stderr plus generated files."""

    logger.info(
        "run_calculix_solver | start | inp_path=%s | run_dir=%s | solver_executable=%s",
        mesh_summary.inp_path,
        config.run_dir,
        config.solver_executable,
    )
    try:
        run_dir = Path(config.run_dir)
        input_path = Path(mesh_summary.inp_path)
        if not input_path.exists():
            raise FileNotFoundError(f"CalculiX input file not found: {input_path}")

        ccx_path = shutil.which(config.solver_executable)
        if not ccx_path:
            raise FileNotFoundError(
                f"CalculiX executable '{config.solver_executable}' was not found on PATH. "
                "Install ccx or update the solver_executable config value."
            )

        stdout_path = run_dir / f"{config.job_name}.stdout.txt"
        stderr_path = run_dir / f"{config.job_name}.stderr.txt"
        command = [ccx_path, config.job_name]
        completed = subprocess.run(
            command,
            cwd=run_dir,
            check=False,
            capture_output=True,
            text=True,
        )

        write_text(stdout_path, completed.stdout or "", force=True)
        write_text(stderr_path, completed.stderr or "", force=True)

        if completed.returncode != 0:
            raise RuntimeError(
                f"CalculiX failed with exit code {completed.returncode}. "
                f"See {stdout_path} and {stderr_path}."
            )

        dat_path = run_dir / f"{config.job_name}.dat"
        frd_path = run_dir / f"{config.job_name}.frd"
        sta_path = run_dir / f"{config.job_name}.sta"
        cvg_path = run_dir / f"{config.job_name}.cvg"
        output_files = sorted(path for path in run_dir.glob(f"{config.job_name}.*") if path.is_file())
        summary = SolverRunSummary(
            job_name=config.job_name,
            run_dir=run_dir,
            input_path=input_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            dat_path=dat_path,
            frd_path=frd_path,
            sta_path=sta_path,
            cvg_path=cvg_path if cvg_path.exists() else None,
            return_code=completed.returncode,
            ccx_executable=ccx_path,
            output_files=output_files,
        )
        logger.info(
            "run_calculix_solver | done | return_code=%s | output_files=%s",
            completed.returncode,
            [path.name for path in output_files],
        )
        return summary
    except Exception:
        logger.exception(
            "run_calculix_solver | failed | inp_path=%s | run_dir=%s | solver_executable=%s",
            mesh_summary.inp_path,
            config.run_dir,
            config.solver_executable,
        )
        raise


def solver_summary_to_dict(summary: SolverRunSummary) -> dict[str, Any]:
    """Convert a solver run summary into a JSON-friendly dictionary."""

    return {
        "job_name": summary.job_name,
        "run_dir": str(summary.run_dir),
        "input_path": str(summary.input_path),
        "stdout_path": str(summary.stdout_path),
        "stderr_path": str(summary.stderr_path),
        "dat_path": str(summary.dat_path),
        "frd_path": str(summary.frd_path),
        "sta_path": str(summary.sta_path),
        "cvg_path": str(summary.cvg_path) if summary.cvg_path is not None else None,
        "return_code": summary.return_code,
        "ccx_executable": summary.ccx_executable,
        "output_files": [str(path) for path in summary.output_files],
    }
