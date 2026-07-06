"""Build the State B FEA-constrained revision prompt for a single CAD sample."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict

from src.prompts.prompt_templates import (
    FEA_PROMPT_CHANGE_LOG_INSTRUCTIONS,
    FEA_PROMPT_CORE_INSTRUCTIONS,
    FEA_PROMPT_HEADER,
    FEA_PROMPT_REQUIREMENT_LABELS,
    FEA_PROMPT_REQUIREMENT_TEXT,
)
from src.schemas.fea import LoadCase, SelectorHints

logger = logging.getLogger(__name__)


def build_fea_prompt(
    original_prompt: str,
    original_code: str,
    load_case: LoadCase,
    selector_hints: SelectorHints,
) -> str:
    """Build a State B revision prompt from State A artifacts and FEA hints."""

    logger.info(
        "build_fea_prompt | start | sample_id=%s | prompt_length=%d | code_length=%d | load_case_keys=%s | selector_hint_keys=%s",
        load_case.sample_id,
        len(original_prompt or ""),
        len(original_code or ""),
        sorted(asdict(load_case).keys()),
        sorted(asdict(selector_hints).keys()),
    )
    try:
        prompt = _render_prompt(original_prompt, original_code, load_case, selector_hints)
        logger.info(
            "build_fea_prompt | done | sample_id=%s | line_count=%d",
            load_case.sample_id,
            len(prompt.splitlines()),
        )
        return prompt
    except Exception:
        logger.exception(
            "build_fea_prompt | failed | sample_id=%s | prompt_length=%d | code_length=%d",
            load_case.sample_id,
            len(original_prompt or ""),
            len(original_code or ""),
        )
        raise


def _render_prompt(
    original_prompt: str,
    original_code: str,
    load_case: LoadCase,
    selector_hints: SelectorHints,
) -> str:
    """Render the revision prompt body from State A and State B inputs."""

    prompt_text = _require_text(original_prompt, "original_prompt")
    code_text = _require_text(original_code, "original_code")
    load_case_json = json.dumps(asdict(load_case), indent=2, sort_keys=True)
    selector_hints_json = json.dumps(asdict(selector_hints), indent=2, sort_keys=True)

    return (
        f"{FEA_PROMPT_HEADER}\n\n"
        "State A original prompt:\n"
        f"{prompt_text}\n\n"
        "State A original DB code:\n"
        "```python\n"
        f"{code_text.rstrip()}\n"
        "```\n\n"
        "Load case (JSON):\n"
        f"{load_case_json}\n\n"
        "Selector hints (JSON):\n"
        f"{selector_hints_json}\n\n"
        "Required content checklist:\n"
        + "\n".join(f"- {item}" for item in FEA_PROMPT_REQUIREMENT_LABELS)
        + "\n\n"
        "State B revision instructions:\n"
        + "\n".join(f"- {item}" for item in FEA_PROMPT_CORE_INSTRUCTIONS)
        + "\n\n"
        "Machine-readable change-log instructions:\n"
        + "\n".join(f"- {item}" for item in FEA_PROMPT_CHANGE_LOG_INSTRUCTIONS)
        + "\n\n"
        "Additional output requirements:\n"
        + "\n".join(f"- {item}" for item in FEA_PROMPT_REQUIREMENT_TEXT)
    )


def _require_text(value: str, label: str) -> str:
    """Return a stripped string or raise a clear validation error."""

    text = (value or "").strip()
    if not text:
        raise ValueError(f"{label} is required for State B prompt construction.")
    return text
