"""Reusable template fragments for State B FEA revision prompt construction."""

from __future__ import annotations

FEA_PROMPT_HEADER = "Revise the original DB CadQuery design with FEA constraints."
FEA_PROMPT_CORE_INSTRUCTIONS = (
    "Preserve the original design identity.",
    "Revise State A instead of designing an unrelated part.",
    "Keep the same functional intent, silhouette, and mounting logic where possible.",
    "Use only permitted modifications such as thickness changes, ribs, gussets, fillets, local strengthening, and support/load face cleanup.",
    "Keep the geometry as one connected solid when possible.",
    "Keep the result meshable and manufacturable.",
    "Do not introduce decorative or unrelated features.",
)
FEA_PROMPT_REQUIREMENT_LABELS = (
    "original prompt",
    "original DB code",
    "load case",
    "selector hints",
    "preserve identity",
    "permitted modifications",
    "machine-readable change log",
)
FEA_PROMPT_CHANGE_LOG_INSTRUCTIONS = (
    "Return a machine-readable change_log object.",
    "Each change_log entry must describe the changed feature, change type, reason, and expected physical effect.",
    "Record whether the original design identity was preserved.",
    "Return only JSON containing code_lines and change_log.",
)
FEA_PROMPT_REQUIREMENT_TEXT = (
    "Prompt output requirement: include original prompt, original DB code, load case, selector hints, identity-preservation rules, and machine-readable change-log instructions.",
    "Code output requirement: return runnable CadQuery Python code using import cadquery as cq and a result variable.",
    "Change-log requirement: describe modifications in a machine-readable structure.",
)
