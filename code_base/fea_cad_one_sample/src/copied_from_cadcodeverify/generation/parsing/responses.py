# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/generation/parsing/responses.py
from __future__ import annotations

import json
import re
import textwrap
from typing import Any, Dict, Iterable, List, Optional


THINK_BLOCK_RE = re.compile(r"query.*?\u2022", re.DOTALL | re.IGNORECASE)
FENCE_BLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]+)?[^\S\r\n]*(?:\r?\n)?(.*?)```", re.DOTALL)
PYTHON_FENCE_RE = re.compile(r"```(?:python|py)[^\S\r\n]*(?:\r?\n)?(.*?)```", re.DOTALL | re.IGNORECASE)
CODE_START_RE = re.compile(
    r"^\s*(?:"
    r"import\b|from\b|def\b|class\b|if\b|elif\b|else:|for\b|while\b|try:|except\b|finally:|with\b|"
    r"return\b|pass\b|continue\b|break\b|assert\b|raise\b|yield\b|"
    r"[A-Za-z_][\w,\s]*\s*=|"
    r"#"
    r")"
)
CADQUERY_MARKERS = (
    "cadquery",
    "cq.",
    "Workplane(",
    ".box(",
    ".circle(",
    ".rect(",
    ".polygon(",
    ".extrude(",
    ".revolve(",
    ".union(",
    ".cut(",
    ".translate(",
    ".faces(",
    ".workplane(",
    ".hole(",
    ".fillet(",
    ".chamfer(",
    "show_object(",
    "exporters.export(",
)
PROSE_PREFIXES = (
    "here is",
    "this code",
    "the code",
    "explanation",
    "it creates",
    "it will",
    "you can",
    "this script",
)


class CodeParsingError(ValueError):
    """Raised when a model response cannot be converted into runnable code."""

    def __init__(self, message: str, raw_response: Optional[str] = None):
        super().__init__(message)
        self.raw_response = raw_response


def _strip_reasoning_noise(text: str) -> str:
    cleaned = THINK_BLOCK_RE.sub("", text or "")
    return cleaned.replace("\r\n", "\n").strip()


def _iter_fenced_blocks(text: str) -> Iterable[str]:
    for match in FENCE_BLOCK_RE.finditer(text):
        block = textwrap.dedent(match.group(1)).strip()
        if block:
            yield block


def _normalize_code(code: str) -> str:
    normalized = textwrap.dedent((code or "").replace("\r\n", "\n")).strip()
    if not normalized:
        raise CodeParsingError("Parsed code is empty.")
    return normalized + "\n"


def _is_code_like_line(line: str, seen_code: bool = False) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("```"):
        return False
    if CODE_START_RE.match(stripped):
        return True
    if any(marker in stripped for marker in CADQUERY_MARKERS):
        return True
    if seen_code and (
        line.startswith((" ", "\t"))
        or stripped.startswith((".", ")", "]", "}", ","))
        or stripped in {"except:", "finally:"}
    ):
        return True
    return False


def _looks_like_prose_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or _is_code_like_line(stripped):
        return False

    lowered = stripped.lower()
    if lowered.startswith(PROSE_PREFIXES):
        return True
    if stripped.endswith(".") and all(marker not in stripped for marker in ("=", "(", ")", "cq.")):
        return True

    words = re.findall(r"[A-Za-z]+", stripped)
    return len(words) >= 7 and all(token.isalpha() for token in words[:7])


def _looks_like_python_code(text: str) -> bool:
    if not text:
        return False

    compact = text.strip()
    if compact.startswith(("{", "[")) and re.search(r'"\s*:\s*', compact):
        return False

    lines = [line.rstrip() for line in text.splitlines()]
    saw_code = False
    code_like_lines = 0
    for line in lines:
        if _is_code_like_line(line, seen_code=saw_code):
            saw_code = True
            code_like_lines += 1

    if code_like_lines >= 2:
        return True

    return any(marker in compact for marker in CADQUERY_MARKERS) and ("=" in compact or "\n" in compact)


def _extract_python_from_text(text: str) -> Optional[str]:
    cleaned = _strip_reasoning_noise(text)
    if not cleaned:
        return None

    for match in PYTHON_FENCE_RE.finditer(cleaned):
        block = textwrap.dedent(match.group(1)).strip()
        if _looks_like_python_code(block):
            return _normalize_code(block)

    for block in _iter_fenced_blocks(cleaned):
        if _looks_like_python_code(block):
            return _normalize_code(block)

    lines = cleaned.splitlines()
    collected: List[str] = []
    start_idx: Optional[int] = None

    for idx, line in enumerate(lines):
        if _is_code_like_line(line):
            start_idx = idx
            break

    if start_idx is not None:
        saw_code = False
        for line in lines[start_idx:]:
            stripped = line.rstrip()
            if not stripped.strip():
                collected.append("")
                continue
            if _is_code_like_line(stripped, seen_code=saw_code):
                collected.append(stripped)
                saw_code = True
                continue
            if saw_code and re.search(r"[=(){}\[\]]", stripped) and not _looks_like_prose_line(stripped):
                collected.append(stripped)
                continue
            if saw_code and _looks_like_prose_line(stripped):
                break
            if saw_code:
                break

        candidate = "\n".join(collected).strip()
        if _looks_like_python_code(candidate):
            return _normalize_code(candidate)

    if _looks_like_python_code(cleaned):
        return _normalize_code(cleaned)

    return None


def _iter_json_objects(text: str) -> Iterable[Dict]:
    cleaned = _strip_reasoning_noise(text)
    if not cleaned:
        return

    decoder = json.JSONDecoder()
    search_spaces = [cleaned, *_iter_fenced_blocks(cleaned)]
    seen_candidates = set()

    for search_space in search_spaces:
        candidate = search_space.strip()
        if not candidate or candidate in seen_candidates:
            continue
        seen_candidates.add(candidate)

        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            obj = None

        if isinstance(obj, dict):
            yield obj

        for idx, ch in enumerate(candidate):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(candidate[idx:])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def _code_from_json_payload(obj: Dict) -> str:
    if not isinstance(obj, dict):
        raise CodeParsingError("Response JSON must be an object.")

    if "code_lines" in obj:
        code_lines = obj.get("code_lines")
        if not isinstance(code_lines, list) or not code_lines or not all(isinstance(line, str) for line in code_lines):
            raise CodeParsingError("Bad JSON: 'code_lines' must be a non-empty list of strings.")
        return _normalize_code("\n".join(line.rstrip() for line in code_lines))

    if "code" in obj:
        code = obj.get("code")
        if not isinstance(code, str):
            raise CodeParsingError("Bad JSON: 'code' must be a string.")
        return _normalize_code(code)

    raise CodeParsingError(f"Bad JSON: missing 'code_lines' or 'code'. Keys: {list(obj.keys())}")


def extract_first_json(text: str) -> Dict:
    """Best-effort extraction of the first JSON object found in text."""
    for obj in _iter_json_objects(text):
        return obj
    raise ValueError("Could not find a complete JSON object in model output.")
