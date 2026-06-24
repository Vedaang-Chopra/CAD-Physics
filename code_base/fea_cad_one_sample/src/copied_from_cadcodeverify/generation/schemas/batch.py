# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/generation/schemas/batch.py
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ...llm.llm import LLMConnector


@dataclass
class GenerationTask:
    dataset_id: str
    model_name: str
    prompt_variant: str
    prompt_text: str
    connector: LLMConnector
    generation_target: Any

    @property
    def custom_id(self) -> str:
        return f"{self.dataset_id}::{self.prompt_variant}"

    @property
    def experiment_name(self) -> str:
        return f"{self.model_name}-{self.prompt_variant}".replace("/", "_")


@dataclass
class HybridGenerationSummary:
    run_id: str
    output_dir: Path
    prepared_tasks: int = 0
    skipped_existing: int = 0
    sync_tasks: int = 0
    batch_tasks: int = 0
    submitted_batches: int = 0
    completed_batches: int = 0
    saved_results: int = 0
    failed_results: int = 0
    batch_ids: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["output_dir"] = str(self.output_dir)
        return data
