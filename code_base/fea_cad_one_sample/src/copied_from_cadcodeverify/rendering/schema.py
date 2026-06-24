# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/visual_analysis/rendering/schema.py
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import create_engine, text


CREATE_RENDERED_VIEWS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cad_rendered_views (
    id BIGSERIAL PRIMARY KEY,
    dataset_id VARCHAR NOT NULL REFERENCES master_metadata(id) ON DELETE CASCADE,
    generation_id BIGINT NULL REFERENCES model_generations(generation_id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    model_name TEXT NULL,
    pipeline_variant TEXT NULL,
    prompt_variant TEXT NULL,
    source_stl_hash TEXT NULL,
    source_artifact_ids JSONB NULL,
    artifact_type TEXT NOT NULL DEFAULT 'pointcloud_debug',
    image_path TEXT NOT NULL,
    view_name TEXT NOT NULL,
    camera_metadata JSONB NOT NULL,
    render_config JSONB NOT NULL,
    render_config_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE cad_rendered_views
    ADD COLUMN IF NOT EXISTS source_artifact_ids JSONB NULL;
ALTER TABLE cad_rendered_views
    ADD COLUMN IF NOT EXISTS artifact_type TEXT NOT NULL DEFAULT 'pointcloud_debug';

ALTER TABLE cad_rendered_views
    DROP CONSTRAINT IF EXISTS chk_cad_rendered_views_source_type;
"""


CREATE_RENDERED_VIEWS_INDEX_SQL = """
DROP INDEX IF EXISTS uq_cad_rendered_views_source_config;

CREATE UNIQUE INDEX IF NOT EXISTS uq_cad_rendered_views_source_artifact_config
    ON cad_rendered_views (
        dataset_id,
        source_type,
        COALESCE(generation_id, 0),
        artifact_type,
        view_name,
        render_config_hash
    );

CREATE INDEX IF NOT EXISTS idx_cad_rendered_views_dataset
    ON cad_rendered_views(dataset_id);

CREATE INDEX IF NOT EXISTS idx_cad_rendered_views_generation
    ON cad_rendered_views(generation_id);
"""


UPSERT_RENDERED_VIEW_SQL = """
INSERT INTO cad_rendered_views (
    dataset_id,
    generation_id,
    source_type,
    model_name,
    pipeline_variant,
    prompt_variant,
    source_stl_hash,
    source_artifact_ids,
    artifact_type,
    image_path,
    view_name,
    camera_metadata,
    render_config,
    render_config_hash,
    status,
    error_message,
    updated_at
)
VALUES (
    :dataset_id,
    :generation_id,
    :source_type,
    :model_name,
    :pipeline_variant,
    :prompt_variant,
    :source_stl_hash,
    CAST(:source_artifact_ids AS JSONB),
    :artifact_type,
    :image_path,
    :view_name,
    CAST(:camera_metadata AS JSONB),
    CAST(:render_config AS JSONB),
    :render_config_hash,
    :status,
    :error_message,
    NOW()
)
ON CONFLICT (
    dataset_id,
    source_type,
    (COALESCE(generation_id, 0)),
    artifact_type,
    view_name,
    render_config_hash
)
DO UPDATE SET
    model_name = EXCLUDED.model_name,
    pipeline_variant = EXCLUDED.pipeline_variant,
    prompt_variant = EXCLUDED.prompt_variant,
    source_stl_hash = EXCLUDED.source_stl_hash,
    source_artifact_ids = EXCLUDED.source_artifact_ids,
    image_path = EXCLUDED.image_path,
    camera_metadata = EXCLUDED.camera_metadata,
    render_config = EXCLUDED.render_config,
    status = EXCLUDED.status,
    error_message = EXCLUDED.error_message,
    updated_at = NOW()
RETURNING id;
"""


def create_rendered_views_schema(connection_string: str) -> None:
    engine = create_engine(connection_string)
    try:
        with engine.begin() as conn:
            conn.execute(text(CREATE_RENDERED_VIEWS_TABLE_SQL))
            conn.execute(text(CREATE_RENDERED_VIEWS_INDEX_SQL))
    finally:
        engine.dispose()


def upsert_rendered_view(connection_string: str, record: Dict[str, Any]) -> Optional[int]:
    engine = create_engine(connection_string)
    try:
        with engine.begin() as conn:
            row = conn.execute(text(UPSERT_RENDERED_VIEW_SQL), record).first()
            return int(row[0]) if row else None
    finally:
        engine.dispose()
