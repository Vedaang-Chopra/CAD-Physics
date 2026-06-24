# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/visual_analysis/rendering/db_loader.py
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

import pandas as pd

from ..db.reader import read_sql_dataframe

from .config import RenderViewsConfig


GROUND_TRUTH_QUERY = """
SELECT
    mm.id AS dataset_id,
    NULL::bigint AS generation_id,
    'ground_truth' AS source_type,
    NULL::text AS model_name,
    NULL::text AS pipeline_variant,
    NULL::text AS prompt_variant,
    NULL::text AS status,
    gt.stl_content AS stl_content,
    NULL::text AS source_stl_hash
FROM master_metadata AS mm
JOIN ground_truth_geometry AS gt
    ON gt.id = mm.id
WHERE gt.stl_content IS NOT NULL
  AND (:dataset_ids_is_null OR mm.id = ANY(:dataset_ids))
ORDER BY
    CASE
        WHEN :dataset_ids_is_null AND :sample_limit_is_set
            THEN md5(mm.id || ':' || CAST(:random_seed AS text))
        ELSE mm.id
    END
LIMIT :sample_limit
"""


GENERATED_QUERY = """
SELECT
    mg.dataset_id,
    mg.generation_id,
    CASE
        WHEN mg.prompt_variant = 'expert' THEN 'generated_expert'
        WHEN mg.prompt_variant = 'non_expert' THEN 'generated_non_expert'
        ELSE 'generated_' || mg.prompt_variant
    END AS source_type,
    mg.model_name,
    mg.pipeline_variant,
    mg.prompt_variant,
    mg.status,
    art.generated_stl AS stl_content,
    art.artifact_hash AS source_stl_hash
FROM model_generations AS mg
JOIN model_generation_artifacts AS art
    ON art.generation_id = mg.generation_id
WHERE art.generated_stl IS NOT NULL
  AND mg.model_name = :model_name
  AND mg.pipeline_variant = :pipeline_variant
  AND mg.prompt_variant = ANY(:prompt_variants)
  AND (:dataset_ids_is_null OR mg.dataset_id = ANY(:dataset_ids))
ORDER BY mg.dataset_id, mg.prompt_variant, mg.generation_id
"""


GENERATED_DATASET_IDS_QUERY = """
SELECT sampled.dataset_id
FROM (
    SELECT DISTINCT mg.dataset_id
    FROM model_generations AS mg
    JOIN model_generation_artifacts AS art
        ON art.generation_id = mg.generation_id
    WHERE art.generated_stl IS NOT NULL
      AND mg.model_name = :model_name
      AND mg.pipeline_variant = :pipeline_variant
      AND mg.prompt_variant = ANY(:prompt_variants)
      AND (:dataset_ids_is_null OR mg.dataset_id = ANY(:dataset_ids))
) AS sampled
ORDER BY
    CASE
        WHEN :dataset_ids_is_null AND :sample_limit_is_set
            THEN md5(sampled.dataset_id || ':' || CAST(:random_seed AS text))
        ELSE sampled.dataset_id
    END
LIMIT :sample_limit
"""


def _query_params(config: RenderViewsConfig) -> Dict[str, Any]:
    return {
        "model_name": config.model_name,
        "pipeline_variant": config.pipeline_variant,
        "prompt_variants": config.prompt_variants,
        "dataset_ids": config.dataset_ids or [],
        "dataset_ids_is_null": config.dataset_ids is None,
        "sample_limit": config.sample_limit,
        "sample_limit_is_set": config.sample_limit is not None,
        "random_seed": config.random_seed,
    }


def load_ground_truth_sources(config: RenderViewsConfig) -> pd.DataFrame:
    params = _query_params(config)
    if config.dataset_ids is not None:
        params["sample_limit"] = max(len(config.dataset_ids), 1)
        params["sample_limit_is_set"] = False
    else:
        params["sample_limit"] = config.sample_limit if config.sample_limit is not None else 1_000_000_000
    return read_sql_dataframe(
        GROUND_TRUTH_QUERY,
        params=params,
        connection_string=config.db_connection_string,
    )


def load_generated_sources(config: RenderViewsConfig, dataset_ids: Optional[List[str]] = None) -> pd.DataFrame:
    params = _query_params(config)
    if dataset_ids is not None:
        params["dataset_ids"] = dataset_ids
        params["dataset_ids_is_null"] = False
    return read_sql_dataframe(
        GENERATED_QUERY,
        params=params,
        connection_string=config.db_connection_string,
    )


def load_generated_dataset_ids(config: RenderViewsConfig) -> List[str]:
    params = _query_params(config)
    if config.dataset_ids is not None:
        params["sample_limit"] = max(len(config.dataset_ids), 1)
        params["sample_limit_is_set"] = False
    else:
        params["sample_limit"] = config.sample_limit if config.sample_limit is not None else 1_000_000_000
    frame = read_sql_dataframe(
        GENERATED_DATASET_IDS_QUERY,
        params=params,
        connection_string=config.db_connection_string,
    )
    if frame.empty:
        return []
    return frame["dataset_id"].astype(str).tolist()


def load_render_sources(config: RenderViewsConfig) -> pd.DataFrame:
    """Load GT rows first, then generated expert/non_expert rows for the same datasets."""
    if "ground_truth" in config.source_types:
        gt_df = load_ground_truth_sources(config)
    else:
        gt_df = pd.DataFrame()
    if gt_df.empty:
        if any(source_type.startswith("generated_") for source_type in config.source_types):
            dataset_ids = config.dataset_ids
            if dataset_ids is None and config.sample_limit is not None:
                dataset_ids = load_generated_dataset_ids(config)
            generated_df = load_generated_sources(config, dataset_ids=dataset_ids)
            generated_df["source_stl_hash"] = generated_df.apply(_source_hash_for_row, axis=1)
            return generated_df.reset_index(drop=True)
        return gt_df

    dataset_ids = gt_df["dataset_id"].astype(str).tolist()
    if any(source_type.startswith("generated_") for source_type in config.source_types):
        generated_df = load_generated_sources(config, dataset_ids=dataset_ids)
    else:
        generated_df = pd.DataFrame()
    combined = pd.concat([gt_df, generated_df], ignore_index=True)
    if combined.empty:
        return combined

    source_order = {
        "ground_truth": 0,
        "generated_expert": 1,
        "generated_non_expert": 2,
    }
    combined["_source_order"] = combined["source_type"].map(source_order).fillna(99)
    combined = combined.sort_values(["dataset_id", "_source_order", "generation_id"], na_position="first")
    combined = combined.drop(columns=["_source_order"]).reset_index(drop=True)
    combined["source_stl_hash"] = combined.apply(_source_hash_for_row, axis=1)
    return combined


def _source_hash_for_row(row: pd.Series) -> str:
    existing_hash = row.get("source_stl_hash")
    if isinstance(existing_hash, str) and existing_hash.strip():
        return existing_hash.strip()
    stl_content = row.get("stl_content")
    if stl_content is None:
        return ""
    return hashlib.sha256(bytes(stl_content)).hexdigest()


def existing_render_records(config: RenderViewsConfig) -> pd.DataFrame:
    query = """
    SELECT dataset_id, source_type, generation_id, artifact_type, view_name, image_path, status, error_message
    FROM cad_rendered_views
    WHERE render_config_hash = :render_config_hash
    ORDER BY dataset_id, source_type, view_name
    """
    params = {"render_config_hash": config.render_config_hash()}
    try:
        return read_sql_dataframe(
            query,
            params=params,
            connection_string=config.db_connection_string,
        )
    except Exception:
        legacy_query = """
        SELECT dataset_id, source_type, generation_id, 'pointcloud_debug' AS artifact_type,
               view_name, image_path, status, error_message
        FROM cad_rendered_views
        WHERE render_config_hash = :render_config_hash
        ORDER BY dataset_id, source_type, view_name
        """
        return read_sql_dataframe(
            legacy_query,
            params=params,
            connection_string=config.db_connection_string,
        )
