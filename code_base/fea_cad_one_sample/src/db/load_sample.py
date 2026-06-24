"""Load a single CAD sample from the database."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.copied_from_cadcodeverify.db.reader import read_sql_dataframe
from src.schemas.sample import CADSample

logger = logging.getLogger(__name__)

_FEA_SENSIBLE_TERMS = (
    "bracket",
    "support",
    "mount",
    "mounting",
    "clamp",
    "plate",
    "beam",
    "arm",
    "frame",
    "connector",
    "cantilever",
    "load",
    "fixture",
)


def load_sample(
    connection_string: str,
    sample_id: str | None = None,
    random: bool = False,
    expert_random: bool = False,
) -> CADSample:
    """Load one sample using exactly one selection mode."""

    logger.info(
        "load_sample | start | sample_id=%s | random=%s | expert_random=%s",
        sample_id,
        random,
        expert_random,
    )
    try:
        selection_count = sum(
            [
                bool(sample_id and str(sample_id).strip()),
                bool(random),
                bool(expert_random),
            ]
        )
        if selection_count != 1:
            raise ValueError("Provide exactly one of sample_id, random, or expert_random.")

        if sample_id and str(sample_id).strip():
            sample = load_sample_by_id(connection_string, sample_id)
        elif random:
            sample = load_random_sample(connection_string)
        else:
            sample = load_expert_random_sample(connection_string)

        logger.info(
            "load_sample | done | sample_id=%s | prompt_variant=%s",
            sample.sample_id,
            sample.prompt_variant,
        )
        return sample
    except Exception:
        logger.exception(
            "load_sample | failed | sample_id=%s | random=%s | expert_random=%s",
            sample_id,
            random,
            expert_random,
        )
        raise


def load_sample_by_id(connection_string: str, sample_id: str) -> CADSample:
    """Load a sample by exact sample_id."""

    logger.info("load_sample_by_id | start | sample_id=%s", sample_id)
    try:
        frame = _run_sample_query(
            connection_string,
            _SAMPLE_BY_ID_QUERY,
            {"sample_id": sample_id},
        )
        sample = _frame_to_sample(frame, selection_mode="sample_id")
        logger.info(
            "load_sample_by_id | done | sample_id=%s | prompt_variant=%s",
            sample.sample_id,
            sample.prompt_variant,
        )
        return sample
    except Exception:
        logger.exception("load_sample_by_id | failed | sample_id=%s", sample_id)
        raise


def load_random_sample(connection_string: str) -> CADSample:
    """Load a random sample with any available prompt."""

    logger.info("load_random_sample | start")
    try:
        frame = _run_sample_query(connection_string, _RANDOM_SAMPLE_QUERY, {})
        sample = _frame_to_sample(frame, selection_mode="random")
        logger.info(
            "load_random_sample | done | sample_id=%s | prompt_variant=%s",
            sample.sample_id,
            sample.prompt_variant,
        )
        return sample
    except Exception:
        logger.exception("load_random_sample | failed")
        raise


def load_expert_random_sample(connection_string: str) -> CADSample:
    """Load a random expert prompt sample biased toward FEA-sensible shapes."""

    logger.info("load_expert_random_sample | start")
    try:
        frame = _run_sample_query(
            connection_string,
            _EXPERT_RANDOM_SAMPLE_QUERY,
            {},
            fallback_query=_EXPERT_RANDOM_FALLBACK_QUERY,
        )
        sample = _frame_to_sample(frame, selection_mode="expert_random")
        logger.info(
            "load_expert_random_sample | done | sample_id=%s | prompt_variant=%s",
            sample.sample_id,
            sample.prompt_variant,
        )
        return sample
    except Exception:
        logger.exception("load_expert_random_sample | failed")
        raise


def _run_sample_query(
    connection_string: str,
    query: str,
    params: dict[str, Any],
    *,
    fallback_query: str | None = None,
) -> pd.DataFrame:
    """Run a sample query and optionally fall back to a broader query."""

    frame = read_sql_dataframe(query, params=params, connection_string=connection_string)
    if not frame.empty or fallback_query is None:
        return frame
    return read_sql_dataframe(fallback_query, params=params, connection_string=connection_string)


def _frame_to_sample(frame: pd.DataFrame, *, selection_mode: str) -> CADSample:
    """Convert a one-row frame into a CADSample."""

    if frame.empty:
        raise LookupError(f"No sample found for selection_mode={selection_mode}.")

    row = frame.iloc[0].to_dict()
    sample_id = str(row.get("sample_id") or row.get("id") or "").strip()
    if not sample_id:
        raise LookupError(f"Sample row missing sample_id for selection_mode={selection_mode}.")

    expert_prompt = _clean_text(row.get("expert_prompt"))
    non_expert_prompt = _clean_text(row.get("non_expert_prompt"))
    prompt = expert_prompt or non_expert_prompt
    if not prompt:
        raise LookupError(f"Sample {sample_id} does not contain prompt text.")

    prompt_variant = "expert" if expert_prompt else "non_expert"
    metadata = {
        "selection_mode": selection_mode,
        "prompt_variant": prompt_variant,
        "ground_truth_code": row.get("ground_truth_code"),
        "non_expert_prompt": non_expert_prompt,
    }
    if expert_prompt:
        metadata["expert_prompt"] = expert_prompt

    return CADSample(
        sample_id=sample_id,
        prompt=prompt,
        prompt_variant=prompt_variant,
        source="cadcodeverify-db",
        metadata=metadata,
        ground_truth_code=None,
    )


def _clean_text(value: Any) -> str:
    """Normalize text values pulled from the database."""

    if value is None:
        return ""
    text = str(value).strip()
    return text


_SAMPLE_BY_ID_QUERY = """
SELECT
    m.id AS sample_id,
    m.expert_prompt,
    m.non_expert_prompt,
    g.python_code AS ground_truth_code
FROM master_metadata AS m
LEFT JOIN ground_truth_code AS g
    ON g.id = m.id
WHERE m.id = :sample_id
LIMIT 1
"""

_RANDOM_SAMPLE_QUERY = """
SELECT
    m.id AS sample_id,
    m.expert_prompt,
    m.non_expert_prompt,
    g.python_code AS ground_truth_code
FROM master_metadata AS m
LEFT JOIN ground_truth_code AS g
    ON g.id = m.id
WHERE NULLIF(TRIM(COALESCE(m.expert_prompt, m.non_expert_prompt, '')), '') IS NOT NULL
ORDER BY RANDOM()
LIMIT 1
"""

_EXPERT_RANDOM_SAMPLE_QUERY = f"""
SELECT
    m.id AS sample_id,
    m.expert_prompt,
    m.non_expert_prompt,
    g.python_code AS ground_truth_code
FROM master_metadata AS m
LEFT JOIN ground_truth_code AS g
    ON g.id = m.id
WHERE NULLIF(TRIM(COALESCE(m.expert_prompt, '')), '') IS NOT NULL
  AND (
    {' OR '.join(f"LOWER(COALESCE(m.expert_prompt, '')) LIKE '%{term}%'" for term in _FEA_SENSIBLE_TERMS)}
  )
ORDER BY RANDOM()
LIMIT 1
"""

_EXPERT_RANDOM_FALLBACK_QUERY = """
SELECT
    m.id AS sample_id,
    m.expert_prompt,
    m.non_expert_prompt,
    g.python_code AS ground_truth_code
FROM master_metadata AS m
LEFT JOIN ground_truth_code AS g
    ON g.id = m.id
WHERE NULLIF(TRIM(COALESCE(m.expert_prompt, '')), '') IS NOT NULL
ORDER BY RANDOM()
LIMIT 1
"""
