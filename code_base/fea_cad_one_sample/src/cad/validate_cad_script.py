"""Validate and extract runnable CadQuery code from model responses."""

from __future__ import annotations

import ast
import logging
from typing import Any

from ..copied_from_cadcodeverify.generation.parsing.responses import (
    CodeParsingError,
    _code_from_json_payload,
    _extract_python_from_text,
    _iter_json_objects,
    _strip_reasoning_noise,
)

logger = logging.getLogger(__name__)


def extract_cadquery_code(raw_response: str) -> str:
    """Extract runnable CadQuery code from a model response string."""

    has_response = bool(raw_response and raw_response.strip())
    logger.info("extract_cadquery_code | start | response_provided=%s", has_response)
    try:
        if not has_response:
            raise ValueError("raw_response must be a non-empty string.")

        cleaned = _strip_reasoning_noise(raw_response)
        for json_obj in _iter_json_objects(cleaned):
            try:
                code = _code_from_json_payload(json_obj)
            except CodeParsingError:
                continue
            return validate_cadquery_code(code)

        extracted = _extract_python_from_text(cleaned)
        if extracted is None:
            raise CodeParsingError("Could not extract runnable CadQuery code.", raw_response=raw_response)
        return validate_cadquery_code(extracted)
    except Exception:
        logger.exception("extract_cadquery_code | failed")
        raise


def validate_cadquery_code(code: str) -> str:
    """Validate a CadQuery Python script and return normalized source text."""

    logger.info("validate_cadquery_code | start")
    try:
        normalized = _normalize_code(code)
        ast.parse(normalized)
        if not _looks_like_cadquery_code(normalized):
            logger.warning("validate_cadquery_code | code has no obvious CadQuery markers")
        logger.info("validate_cadquery_code | done | line_count=%d", len(normalized.splitlines()))
        return normalized
    except Exception:
        logger.exception("validate_cadquery_code | failed")
        raise


def extract_and_validate_cadquery_code(raw_response: str) -> str:
    """Extract and validate runnable CadQuery code from a raw model response."""

    logger.info("extract_and_validate_cadquery_code | start")
    try:
        code = extract_cadquery_code(raw_response)
        logger.info("extract_and_validate_cadquery_code | done")
        return code
    except Exception:
        logger.exception("extract_and_validate_cadquery_code | failed")
        raise


def _normalize_code(code: str) -> str:
    """Normalize extracted source into a trailing-newline Python script."""

    text = str(code or "").replace("\r\n", "\n").strip()
    if not text:
        raise ValueError("code must be a non-empty string.")
    return text + "\n"


def _looks_like_cadquery_code(code: str) -> bool:
    """Return True when the script contains obvious CadQuery markers."""

    lowered = code.lower()
    markers = (
        "cadquery",
        "cq.",
        "workplane(",
        ".box(",
        ".extrude(",
        ".cut(",
        ".union(",
        "result =",
    )
    return any(marker in lowered for marker in markers)
