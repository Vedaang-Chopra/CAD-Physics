"""Local no-op observability helpers for the copied LLM connector."""

from __future__ import annotations

from typing import Any, Optional

langfuse_observation: Any = None


def summary_metadata_from_text(*, text: Optional[str], limit: int = 1200) -> str:
    """Return a compact preview string for optional telemetry payloads."""

    value = "" if text is None else str(text)
    return value[:limit].rstrip() + "... [truncated]" if len(value) > limit else value
