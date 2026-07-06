"""Parse CalculiX output and evaluate pass/fail criteria."""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import Any

from .schemas import FEAReplicationConfig, ParsedResultSummary, SolverRunSummary
from .utils import write_json

logger = logging.getLogger(__name__)

_HEADER_RE = re.compile(r" (.+?)for .*set\s*(\S+) and time (.+)")
_FLOAT_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[Ee][-+]?\d+)?")


def parse_calculix_results(config: FEAReplicationConfig, solver_summary: SolverRunSummary) -> ParsedResultSummary:
    """Parse the CalculiX .dat file and evaluate the verification criteria."""

    logger.info(
        "parse_calculix_results | start | dat_path=%s | yield_strength_pa=%s",
        solver_summary.dat_path,
        config.material.yield_strength_pa,
    )
    try:
        dat_path = Path(solver_summary.dat_path)
        if not dat_path.exists():
            raise FileNotFoundError(f"CalculiX .dat file not found: {dat_path}")

        blocks = _parse_dat_blocks(dat_path)
        displacement = _extract_max_displacement(blocks)
        stress = _extract_max_stress(blocks)
        notes: list[str] = []
        if stress is None:
            notes.append(
                "Stress parsing TODO: no usable *EL PRINT stress block was detected in the .dat file. "
                "The pipeline still records displacement results."
            )

        max_displacement_mm = displacement["max_magnitude_mm"] if displacement else None
        max_displacement_node = displacement["node_id"] if displacement else None
        max_von_mises_mpa = stress["max_von_mises_mpa"] if stress else None
        max_von_mises_element = stress["element_id"] if stress else None
        estimated_safety_factor = (
            config.material.yield_strength_pa / (max_von_mises_mpa * 1_000_000.0)
            if max_von_mises_mpa not in (None, 0)
            else None
        )
        passes_displacement = (
            max_displacement_mm is not None and max_displacement_mm <= config.verification_criteria.max_displacement_mm
        )
        passes_safety_factor = (
            estimated_safety_factor is not None
            and estimated_safety_factor >= config.verification_criteria.required_safety_factor
        )
        overall_pass = (passes_displacement and passes_safety_factor) if max_von_mises_mpa is not None else None
        summary_path = dat_path.with_name("parsed_results.json")
        summary = ParsedResultSummary(
            job_name=solver_summary.job_name,
            dat_path=dat_path,
            summary_path=summary_path,
            max_displacement_mm=max_displacement_mm,
            max_displacement_node=max_displacement_node,
            max_von_mises_mpa=max_von_mises_mpa,
            max_von_mises_element=max_von_mises_element,
            estimated_safety_factor=estimated_safety_factor,
            passes_displacement=passes_displacement,
            passes_safety_factor=passes_safety_factor if max_von_mises_mpa is not None else None,
            overall_pass=overall_pass,
            notes=notes,
        )
        write_json(summary_path, parsed_result_summary_to_dict(summary), force=True)
        logger.info(
            "parse_calculix_results | done | max_displacement_mm=%s | max_von_mises_mpa=%s | overall_pass=%s",
            max_displacement_mm,
            max_von_mises_mpa,
            overall_pass,
        )
        return summary
    except Exception:
        logger.exception("parse_calculix_results | failed | dat_path=%s", solver_summary.dat_path)
        raise


def parsed_result_summary_to_dict(summary: ParsedResultSummary) -> dict[str, Any]:
    """Convert parsed results to a JSON-friendly dictionary."""

    return {
        "job_name": summary.job_name,
        "dat_path": str(summary.dat_path),
        "summary_path": str(summary.summary_path),
        "max_displacement_mm": summary.max_displacement_mm,
        "max_displacement_node": summary.max_displacement_node,
        "max_von_mises_mpa": summary.max_von_mises_mpa,
        "max_von_mises_element": summary.max_von_mises_element,
        "estimated_safety_factor": summary.estimated_safety_factor,
        "passes_displacement": summary.passes_displacement,
        "passes_safety_factor": summary.passes_safety_factor,
        "overall_pass": summary.overall_pass,
        "notes": list(summary.notes),
    }


def _parse_dat_blocks(dat_path: Path) -> list[dict[str, Any]]:
    """Split a CalculiX .dat file into labeled result blocks."""

    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in dat_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.rstrip()
        header = _HEADER_RE.match(line)
        if header:
            if current is not None:
                blocks.append(current)
            current = {
                "label": header.group(1).strip().lower(),
                "set_name": header.group(2).strip(),
                "time": header.group(3).strip(),
                "lines": [],
            }
            continue
        if current is None:
            continue
        if not line.strip():
            if current["lines"]:
                blocks.append(current)
            current = None
            continue
        current["lines"].append(line)
    if current is not None:
        blocks.append(current)
    return blocks


def _extract_max_displacement(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the largest displacement magnitude found in the parsed blocks."""

    for block in blocks:
        label = str(block.get("label", ""))
        if "displacement" not in label and label != "u":
            continue
        best: dict[str, Any] | None = None
        for line in block.get("lines", []):
            numbers = _parse_numbers(line)
            if len(numbers) < 4:
                continue
            node_id = int(round(numbers[0]))
            ux, uy, uz = numbers[-3], numbers[-2], numbers[-1]
            magnitude_mm = math.sqrt(ux * ux + uy * uy + uz * uz)
            if best is None or magnitude_mm > best["max_magnitude_mm"]:
                best = {
                    "node_id": node_id,
                    "ux_mm": ux,
                    "uy_mm": uy,
                    "uz_mm": uz,
                    "max_magnitude_mm": magnitude_mm,
                    "set_name": block.get("set_name"),
                    "time": block.get("time"),
                }
        if best is not None:
            return best
    return None


def _extract_max_stress(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the largest von Mises stress found in the parsed blocks."""

    for block in blocks:
        label = str(block.get("label", ""))
        if "stress" not in label and label not in {"s", "mises"}:
            continue
        best: dict[str, Any] | None = None
        for line in block.get("lines", []):
            numbers = _parse_numbers(line)
            if len(numbers) >= 7:
                element_id = int(round(numbers[0]))
                stress_components = numbers[1:7]
                von_mises_mpa = _von_mises_from_components(stress_components)
            elif len(numbers) == 2:
                element_id = int(round(numbers[0]))
                von_mises_mpa = abs(numbers[1])
            else:
                continue
            if best is None or von_mises_mpa > best["max_von_mises_mpa"]:
                best = {
                    "element_id": element_id,
                    "max_von_mises_mpa": von_mises_mpa,
                    "set_name": block.get("set_name"),
                    "time": block.get("time"),
                }
        if best is not None:
            return best
    return None


def _parse_numbers(line: str) -> list[float]:
    """Extract all floating-point values from one line."""

    return [float(match) for match in _FLOAT_RE.findall(line)]


def _von_mises_from_components(components: list[float]) -> float:
    """Compute von Mises stress from a 6-component stress vector."""

    if len(components) < 6:
        raise ValueError("Expected six stress components to compute von Mises stress.")
    sxx, syy, szz, sxy, sxz, syz = components[:6]
    return math.sqrt(
        0.5
        * (
            (sxx - syy) ** 2
            + (syy - szz) ** 2
            + (szz - sxx) ** 2
            + 6.0 * (sxy * sxy + sxz * sxz + syz * syz)
        )
    )
