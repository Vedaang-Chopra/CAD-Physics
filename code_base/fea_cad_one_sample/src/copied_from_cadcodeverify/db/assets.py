# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/load_data/data_loading/assets.py
"""Generic ground-truth asset loader."""
from __future__ import annotations

from typing import Any, Dict, Iterable


def load_ground_truth_assets_by_source_id(conn, source_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """Load ground-truth STL bytes and CadQuery code by source_id.

    Args:
        conn: An open psycopg2 connection.
        source_ids: Iterable of string source identifiers.

    Returns:
        Dict mapping source_id -> {"gt_stl_bytes": bytes, "ground_truth_code": str}.
    """
    unique_source_ids = sorted({str(source_id) for source_id in source_ids if source_id})
    if not unique_source_ids:
        return {}

    query = """
        SELECT
            m.id,
            geom.stl_content,
            code.python_code
        FROM master_metadata m
        LEFT JOIN ground_truth_geometry geom
            ON geom.id = m.id
        LEFT JOIN ground_truth_code code
            ON code.id = m.id
        WHERE m.id = ANY(%s)
    """
    with conn.cursor() as cur:
        cur.execute(query, (unique_source_ids,))
        rows = cur.fetchall()

    return {
        str(source_id): {
            "gt_stl_bytes": stl_content,
            "ground_truth_code": python_code if isinstance(python_code, str) else "",
        }
        for source_id, stl_content, python_code in rows
        if stl_content
    }
