# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/visual_analysis/rendering/config.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


DEFAULT_VIEWS = (
    "front",
    "back",
    "left",
    "right",
    "top",
    "bottom",
    "isometric_1",
    "isometric_2",
    "isometric_3",
)
LEGACY_VIEWS = ("front", "back", "left", "right", "top", "bottom", "isometric")
DEFAULT_RENDER_MODES = ("shaded", "silhouette", "depth", "normal", "edge", "slice")
DEFAULT_SLICE_VIEWS = ("slice_xy_mid", "slice_yz_mid", "slice_xz_mid")
DEFAULT_COMPARISON_ARTIFACTS = ("overlay", "silhouette_diff", "depth_diff", "edge_diff")
DEFAULT_PROMPT_VARIANTS = ("expert", "non_expert")
DEFAULT_SOURCE_TYPES = ("ground_truth", "generated_expert", "generated_non_expert")
VALID_BACKGROUNDS = ("white", "transparent")
VALID_RENDER_MODES = (
    "shaded",
    "silhouette",
    "depth",
    "normal",
    "edge",
    "slice",
    "pointcloud_debug",
)
VALID_COMPARISON_ARTIFACTS = ("overlay", "silhouette_diff", "depth_diff", "edge_diff")


def _default_output_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "execution_results" / "generation_metadata" / "grid_visuals" / "artifacts"


def _normalize_sequence(values: Optional[Iterable[str]], default: Sequence[str]) -> List[str]:
    if values is None:
        return list(default)
    normalized = [str(value).strip() for value in values if str(value).strip()]
    return normalized or list(default)


@dataclass(frozen=True)
class RenderViewsConfig:
    """Configuration for rendering CAD ground-truth and generated STL artifacts."""

    db_connection_string: Optional[str] = None
    model_name: str = "gpt_oss_120b"
    pipeline_variant: str = "rag"
    prompt_variants: List[str] = field(default_factory=lambda: list(DEFAULT_PROMPT_VARIANTS))
    source_types: List[str] = field(default_factory=lambda: list(DEFAULT_SOURCE_TYPES))
    dataset_ids: Optional[List[str]] = None
    output_dir: Path = field(default_factory=_default_output_dir)
    views: List[str] = field(default_factory=lambda: list(DEFAULT_VIEWS))
    render_modes: List[str] = field(default_factory=lambda: list(DEFAULT_RENDER_MODES))
    slice_views: List[str] = field(default_factory=lambda: list(DEFAULT_SLICE_VIEWS))
    comparison_artifact_types: List[str] = field(default_factory=lambda: list(DEFAULT_COMPARISON_ARTIFACTS))
    include_comparisons: bool = True
    legacy_pointcloud_views: bool = False
    random_view_count: int = 0
    random_seed: int = 0
    resolution: int = 512
    background: str = "white"
    point_sample_count: int = 20000
    point_size: float = 0.8
    overwrite_existing: bool = False
    sample_limit: Optional[int] = 3
    batch_size: Optional[int] = None
    db_save_enabled: bool = True
    create_schema: bool = True
    dry_run: bool = False

    @classmethod
    def from_dict(cls, values: Dict[str, Any]) -> "RenderViewsConfig":
        data = dict(values)
        if "output_dir" in data and data["output_dir"] is not None:
            data["output_dir"] = Path(data["output_dir"]).expanduser()
        if "views" in data:
            data["views"] = _normalize_sequence(data["views"], DEFAULT_VIEWS)
        if "prompt_variants" in data:
            data["prompt_variants"] = _normalize_sequence(
                data["prompt_variants"], DEFAULT_PROMPT_VARIANTS
            )
        if "source_types" in data:
            data["source_types"] = _normalize_sequence(data["source_types"], DEFAULT_SOURCE_TYPES)
        if "render_modes" in data:
            data["render_modes"] = _normalize_sequence(data["render_modes"], DEFAULT_RENDER_MODES)
        if "slice_views" in data:
            data["slice_views"] = _normalize_sequence(data["slice_views"], DEFAULT_SLICE_VIEWS)
        if "comparison_artifact_types" in data:
            data["comparison_artifact_types"] = _normalize_sequence(
                data["comparison_artifact_types"], DEFAULT_COMPARISON_ARTIFACTS
            )
        if "dataset_ids" in data and data["dataset_ids"] is not None:
            data["dataset_ids"] = _normalize_sequence(data["dataset_ids"], ())
        return cls(**data)

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_dir", Path(self.output_dir).expanduser())
        object.__setattr__(self, "views", _normalize_sequence(self.views, DEFAULT_VIEWS))
        object.__setattr__(
            self,
            "prompt_variants",
            _normalize_sequence(self.prompt_variants, DEFAULT_PROMPT_VARIANTS),
        )
        object.__setattr__(
            self,
            "source_types",
            _normalize_sequence(self.source_types, DEFAULT_SOURCE_TYPES),
        )
        object.__setattr__(
            self,
            "render_modes",
            _normalize_sequence(self.render_modes, DEFAULT_RENDER_MODES),
        )
        object.__setattr__(
            self,
            "slice_views",
            _normalize_sequence(self.slice_views, DEFAULT_SLICE_VIEWS),
        )
        object.__setattr__(
            self,
            "comparison_artifact_types",
            _normalize_sequence(self.comparison_artifact_types, DEFAULT_COMPARISON_ARTIFACTS),
        )
        if self.dataset_ids is not None:
            object.__setattr__(self, "dataset_ids", _normalize_sequence(self.dataset_ids, ()))
        if self.resolution <= 0:
            raise ValueError("resolution must be positive.")
        if self.point_sample_count <= 0:
            raise ValueError("point_sample_count must be positive.")
        if self.random_view_count < 0:
            raise ValueError("random_view_count must be non-negative.")
        if self.background not in VALID_BACKGROUNDS:
            raise ValueError(f"background must be one of {VALID_BACKGROUNDS}.")
        invalid_modes = sorted(set(self.render_modes) - set(VALID_RENDER_MODES))
        if invalid_modes:
            raise ValueError(f"unsupported render mode(s): {invalid_modes}")
        invalid_comparisons = sorted(set(self.comparison_artifact_types) - set(VALID_COMPARISON_ARTIFACTS))
        if invalid_comparisons:
            raise ValueError(f"unsupported comparison artifact(s): {invalid_comparisons}")

    @property
    def all_view_names(self) -> List[str]:
        random_names = [f"random_{idx + 1:02d}" for idx in range(self.random_view_count)]
        return [*self.views, *random_names]

    @property
    def enabled_render_modes(self) -> List[str]:
        modes = list(self.render_modes)
        if self.legacy_pointcloud_views and "pointcloud_debug" not in modes:
            modes.append("pointcloud_debug")
        return modes

    @property
    def enabled_artifact_types(self) -> List[str]:
        artifact_types = list(self.enabled_render_modes)
        if self.slice_views and "slice" in artifact_types:
            return artifact_types
        return [mode for mode in artifact_types if mode != "slice"]

    def render_config_payload(self) -> Dict[str, Any]:
        return {
            "views": list(self.views),
            "render_modes": list(self.enabled_render_modes),
            "slice_views": list(self.slice_views),
            "comparison_artifact_types": list(self.comparison_artifact_types),
            "include_comparisons": self.include_comparisons,
            "source_types": list(self.source_types),
            "random_view_count": self.random_view_count,
            "random_seed": self.random_seed,
            "resolution": self.resolution,
            "background": self.background,
            "point_sample_count": self.point_sample_count,
            "point_size": self.point_size,
            "projection": "orthographic",
            "normalization": "dataset_shared_centered_unit_extent",
            "renderer": "trimesh_cpu_orthographic_raster",
        }

    def render_config_hash(self) -> str:
        payload = json.dumps(self.render_config_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
