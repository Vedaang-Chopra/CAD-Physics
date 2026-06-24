"""Schema definitions for one-sample CAD samples."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CADSample:
    """A single CAD sample and its source metadata."""

    sample_id: str
    prompt: str
    prompt_variant: str
    source: str
    metadata: dict[str, Any]
    ground_truth_code: str | None = None
