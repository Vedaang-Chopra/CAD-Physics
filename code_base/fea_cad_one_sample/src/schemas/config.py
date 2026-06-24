"""Schema definitions for one-sample pipeline configuration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineConfig:
    """Runtime configuration for the one-sample CAD-to-FEA pipeline."""

    config_name: str
    config_path: Path
    output_root: Path
    force: bool = False
    num_views: int = 4
