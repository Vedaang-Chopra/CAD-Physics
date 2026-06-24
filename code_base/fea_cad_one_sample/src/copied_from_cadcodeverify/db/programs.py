# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/load_data/data_loading/programs.py
"""Generic database program loaders.

These functions load program records from the database without any
feature-specific graph logic. They are the canonical source for
expert, generated, and prompt-source records.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def load_expert_programs(conn) -> List[Dict[str, Any]]:
    """Load all ground-truth CadQuery programs from the DB.

    Args:
        conn: An open psycopg2 connection.

    Returns:
        List of program record dicts with keys: id, expert_prompt, python_code.
    """
    query = """
        SELECT m.id, m.expert_prompt, g.python_code
        FROM master_metadata m
        JOIN ground_truth_code g ON g.id = m.id
        WHERE g.python_code IS NOT NULL
        ORDER BY m.id
    """
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    programs = [{"id": row[0], "expert_prompt": row[1], "python_code": row[2]} for row in rows]
    print(f"Loaded {len(programs)} expert programs from the database.")
    return programs


def load_prompt_sources(conn) -> List[Dict[str, Any]]:
    """Load all prompt-source records from the DB.

    Args:
        conn: An open psycopg2 connection.

    Returns:
        List of prompt-source record dicts with keys: id, expert_prompt, non_expert_prompt.
    """
    query = """
        SELECT id, expert_prompt, non_expert_prompt
        FROM master_metadata
        WHERE expert_prompt IS NOT NULL OR non_expert_prompt IS NOT NULL
        ORDER BY id
    """
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    prompt_rows = [{"id": row[0], "expert_prompt": row[1], "non_expert_prompt": row[2]} for row in rows]
    print(f"Loaded {len(prompt_rows)} prompt rows from the database.")
    return prompt_rows


def load_generated_programs(
    conn,
    model_name: str,
    pipeline_variant: str = "baseline",
    prompt_variant: str = "expert",
) -> List[Dict[str, Any]]:
    """Load generated CadQuery programs from the DB with optional filters.

    Args:
        conn: An open psycopg2 connection.
        model_name: Filter on model_name column.
        pipeline_variant: Filter on pipeline_variant column.
        prompt_variant: Must be "expert" or "non_expert".

    Returns:
        List of generated program record dicts.
    """
    if prompt_variant not in {"expert", "non_expert"}:
        raise ValueError("prompt_variant must be 'expert' or 'non_expert'.")

    query = """
        WITH latest_generations AS (
            SELECT
                mg.generation_id,
                mg.dataset_id,
                mg.model_name,
                mg.pipeline_variant,
                mg.status,
                ROW_NUMBER() OVER (
                    PARTITION BY mg.dataset_id
                    ORDER BY mg.created_at DESC, mg.generation_id DESC
                ) AS rn
            FROM model_generations mg
            WHERE mg.model_name = %s
              AND mg.pipeline_variant = %s
              AND mg.prompt_variant = %s
        )
        SELECT
            lg.generation_id,
            CAST(lg.dataset_id AS VARCHAR) AS dataset_id,
            lg.model_name,
            lg.pipeline_variant,
            m.expert_prompt,
            m.non_expert_prompt,
            code.generated_code,
            lg.status,
            ev.metrics
        FROM latest_generations lg
        LEFT JOIN model_generation_code code
            ON code.generation_id = lg.generation_id
        LEFT JOIN model_generation_evaluations ev
            ON ev.generation_id = lg.generation_id
        JOIN master_metadata m
            ON CAST(m.id AS VARCHAR) = CAST(lg.dataset_id AS VARCHAR)
        WHERE lg.rn = 1
        ORDER BY lg.dataset_id
    """

    with conn.cursor() as cur:
        cur.execute(query, (model_name, pipeline_variant, prompt_variant))
        rows = cur.fetchall()

    programs = []
    for generation_id, dataset_id, loaded_model_name, loaded_pipeline_variant, expert_prompt, non_expert_prompt, generated_code, status, metrics in rows:
        prompt = expert_prompt if prompt_variant == "expert" else non_expert_prompt
        programs.append(
            {
                "generation_id": int(generation_id),
                "id": str(dataset_id),
                "model_name": loaded_model_name,
                "pipeline_variant": loaded_pipeline_variant,
                "prompt_variant": prompt_variant,
                "prompt": prompt,
                "expert_prompt": expert_prompt,
                "non_expert_prompt": non_expert_prompt,
                "generated_code": generated_code,
                "status": status,
                "metrics": metrics if isinstance(metrics, dict) else {},
            }
        )

    print(
        "Loaded "
        f"{len(programs)} generated programs for "
        f"model_name={model_name}, pipeline_variant={pipeline_variant}, prompt_variant={prompt_variant}."
    )
    return programs
