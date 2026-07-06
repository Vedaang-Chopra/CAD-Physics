# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/load_data/core/paths.py
"""Path resolution utilities for the code_base directory."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def resolve_code_base(start_path: Optional[Path] = None) -> Path:
    """Resolve the repository ``code_base`` directory from a starting path.

    The notebooks may be executed from different working directories. This
    helper walks up the current path and accepts either of these layouts:

    - ``.../code_base``
    - ``.../<repo_root>/code_base``

    Args:
        start_path: Optional starting path. Defaults to ``Path.cwd()``.

    Returns:
        Absolute path to the ``code_base`` directory.

    Raises:
        RuntimeError: If the code_base directory cannot be found.
    """
    start = (start_path or Path.cwd()).resolve()
    search_roots = [start, *start.parents]

    for candidate in search_roots:
        if candidate.name == "code_base" and (candidate / "src").exists():
            return candidate
        nested_code_base = candidate / "code_base"
        if nested_code_base.exists() and (nested_code_base / "src").exists():
            return nested_code_base

    raise RuntimeError("Could not locate code_base from the current working directory.")
