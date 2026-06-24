# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/generation/services/generator.py
from __future__ import annotations

import re
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ...execution.python_kernel import PythonKernel
from ...llm.llm import LLMConnector

from ..parsing.responses import (
    CodeParsingError,
    extract_first_json,
    _code_from_json_payload,
    _extract_python_from_text,
    _iter_json_objects,
    _strip_reasoning_noise,
)
from ..schemas.batch import GenerationTask


CADQUERY_CODEGEN_PROMPT_PREFIX = textwrap.dedent(
    """\
    You are a 3D modeling assistant with expertise in the CadQuery Python library.

    You will be given a natural language description of a 3D object. Your task is to generate runnable CadQuery code for that object.

    # Natural language description:
    """
)
CADQUERY_CODEGEN_PROMPT_SUFFIX = textwrap.dedent(
    """\

    Now, write the corresponding CadQuery code following the JSON format exactly.
    The code_lines must be valid Python, import cadquery as cq, and assign the final CadQuery Workplane/Solid to a variable named result.
    """
)

DEFAULT_PROMPT_CACHE_KEY = "cadcodeverify_codegen_v1"
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


class Generator:
    def __init__(self, connector: LLMConnector, config: Dict):
        self.connector = connector
        self.config = config
        self.generation_config = config.get("generation", {})
        self.output_schema = self.generation_config.get("output_schema")
        self.kernel = PythonKernel(timeout=60)

    def _get_response_format(self) -> Optional[Dict]:
        if not self.output_schema:
            return None
        return {
            "type": "json_schema",
            "json_schema": self.output_schema,
        }

    def _prompt_cache_kwargs(self, purpose: str) -> Dict[str, str]:
        cache_cfg = self.generation_config.get("prompt_cache", {})
        if cache_cfg is None:
            cache_cfg = {}
        if not isinstance(cache_cfg, dict):
            cache_cfg = {"enabled": bool(cache_cfg)}

        if cache_cfg.get("enabled", True) is False:
            return {}

        cache_key = cache_cfg.get("key") or DEFAULT_PROMPT_CACHE_KEY
        kwargs = {"prompt_cache_key": f"{cache_key}:{purpose}"}
        retention = cache_cfg.get("retention")
        if retention:
            kwargs["prompt_cache_retention"] = str(retention)
        return kwargs

    def build_generation_user_message(self, prompt: str, preformatted: bool = False) -> str:
        if preformatted:
            return prompt
        return f"{CADQUERY_CODEGEN_PROMPT_PREFIX}{prompt}{CADQUERY_CODEGEN_PROMPT_SUFFIX}"

    def build_generation_request_kwargs(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        preformatted: bool = False,
    ) -> Dict[str, Any]:
        user_message = self.build_generation_user_message(prompt, preformatted=preformatted)
        return {
            "prompt": user_message,
            "system_instruction": self._compose_system_instruction(system_instruction),
            "response_format": self._get_response_format(),
            "temperature": self.generation_config.get("temperature", 0.0),
            "max_tokens": self.generation_config.get("max_tokens", 3000),
            **self._prompt_cache_kwargs("generation"),
        }

    def _compose_system_instruction(self, base_instruction: Optional[str]) -> str:
        base = (base_instruction or "").strip()
        if self.output_schema:
            structured = "Return only JSON matching the provided schema."
        else:
            structured = "Return only JSON with either a 'code_lines' array or a 'code' string."
        structured += " Do not include markdown fences, prose, or reasoning."
        return f"{base}\n\n{structured}" if base else structured

    def _format_status(self, prefix: str, detail: Optional[str] = None, limit: int = 160) -> str:
        cleaned_detail = re.sub(r"\s+", " ", str(detail or "")).strip()
        if not cleaned_detail:
            return prefix

        budget = max(limit - len(prefix) - 2, 0)
        if len(cleaned_detail) > budget:
            cleaned_detail = cleaned_detail[: max(budget - 3, 0)].rstrip() + "..."
        return f"{prefix}: {cleaned_detail}"

    def _log_response_preview(self, label: str, raw_response: Optional[str]) -> None:
        preview = _strip_reasoning_noise(raw_response or "")
        preview = preview.replace("\n", "\\n")
        if len(preview) > 300:
            preview = preview[:300] + "..."
        print(f"{label}. Raw response preview: {preview or '<empty>'}")

    def _recover_code_from_response(self, raw_response: str, purpose: str) -> str:
        prompt = f"""
        The previous {purpose} response was malformed or not compliant with the requested schema.
        Extract the runnable CadQuery Python code from it and return only valid JSON matching the schema.
        Do not include any explanation.

        Previous response:
        ```text
        {raw_response}
        ```
        """

        response = self.connector.generate(
            prompt=prompt,
            system_instruction=self._compose_system_instruction(
                "You normalize malformed LLM responses into structured CadQuery code output."
            ),
            response_format=self._get_response_format(),
            temperature=0.0,
            max_tokens=self.generation_config.get("max_tokens", 3000),
            **self._prompt_cache_kwargs("recovery"),
        )
        return self.parse_code(response)

    def _parse_or_recover_code(self, raw_response: str, purpose: str) -> str:
        try:
            return self.parse_code(raw_response)
        except CodeParsingError as parse_error:
            self._log_response_preview(f"{purpose} parse failed", raw_response)
            try:
                return self._recover_code_from_response(raw_response, purpose)
            except Exception as recovery_error:
                parse_message = str(parse_error).rstrip(".")
                recovery_message = str(recovery_error).rstrip(".")
                raise CodeParsingError(
                    f"{parse_message}. Recovery failed: {recovery_message}",
                    raw_response=raw_response,
                ) from recovery_error

    def generate_code_raw(self, prompt: str, system_instruction: Optional[str], preformatted: bool = False) -> str:
        """Calls the LLM to generate code.

        Args:
            preformatted: If True, `prompt` is already a fully structured user message
                (e.g. from run_generation_with_context) and is sent as-is, skipping
                the standard instruction_cot wrapper to avoid double-wrapping.
        """
        response = self.connector.generate(
            **self.build_generation_request_kwargs(
                prompt,
                system_instruction=system_instruction,
                preformatted=preformatted,
            )
        )
        return response

    def parse_code(self, content: str) -> str:
        """Parses JSON or salvages Python content to extract runnable code."""
        cleaned = _strip_reasoning_noise(content or "")
        if not cleaned:
            raise CodeParsingError("Empty model response.", raw_response=content)

        json_errors: List[str] = []
        for obj in _iter_json_objects(cleaned):
            try:
                return _code_from_json_payload(obj)
            except CodeParsingError as exc:
                json_errors.append(str(exc))

        salvaged = _extract_python_from_text(cleaned)
        if salvaged:
            return salvaged

        detail = json_errors[0] if json_errors else "No valid JSON or runnable Python code found in model output."
        raise CodeParsingError(detail, raw_response=content)

    def fix_code(self, code_content: str, error_message: str, error_context: Optional[str] = None) -> str:
        """Attempts to fix the code given the error message."""
        instruction_fix = """
        You will be given a snippet of Python code along with a corresponding compiler error message. Your task is to:
        1. Analyze the error message and identify the underlying issue in the code.
        2. Correct the bug(s) in the code.
        3. Rewrite the corrected version of the code.
        Return JSON with 'code' or 'code_lines'.
        """

        if error_context:
            instruction_fix += (
                "\n\nHere is some documentation that may be relevant to the error:\n\n"
                f"{error_context}\n\nPlease use this documentation to fix the invalid CadQuery operations.\n"
            )

        prompt = f"{instruction_fix}\nError:\n{error_message}\n\nCode:\n```python\n{code_content}\n```\n"

        response = self.connector.generate(
            prompt=prompt,
            system_instruction=self._compose_system_instruction(
                "You repair CadQuery Python code and return only the corrected code."
            ),
            response_format=self._get_response_format(),
            temperature=0.0,
            max_tokens=4000,
            **self._prompt_cache_kwargs("fix"),
        )

        return self._parse_or_recover_code(response, purpose="fix")

    def _build_export_logic(self, stl_filename: str) -> str:
        return f'''

import cadquery as cq
try:
    if 'result' in locals() and isinstance(locals()['result'], cq.Workplane):
        cq.exporters.export(result, '{stl_filename}')
    else:
        exported = False
        for var_name, var_val in reversed(list(locals().items())):
            if isinstance(var_val, cq.Workplane):
                cq.exporters.export(var_val, '{stl_filename}')
                exported = True
                break
except Exception:
    pass
'''

    def execute_generated_response(
        self,
        working_dir: Path,
        raw_response: str,
        experiment_name: str,
        do_fix: bool = True,
        error_retriever: Optional[Callable[[str], str]] = None,
    ) -> Tuple[str, str, Optional[bytes], bool]:
        """Parse, execute, optionally repair, and collect an STL from a model response."""
        script_filename = f"{experiment_name}.py"
        stl_filename = f"{experiment_name}.stl"
        stl_path = working_dir / stl_filename

        final_code = ""
        status = "Failed"
        stl_binary = None
        success = False

        try:
            try:
                final_code = self._parse_or_recover_code(raw_response, purpose="generation")
            except CodeParsingError as parse_error:
                status = self._format_status("Parse failed", str(parse_error))
                return "", status, None, False

            export_logic = self._build_export_logic(stl_filename)
            code_to_run = final_code + export_logic

            exec_success, out, err = self.kernel.run_code(code_to_run, working_dir, script_filename)

            if not exec_success and do_fix:
                print("Attempting to fix code...")
                error_context = None
                if error_retriever:
                    try:
                        error_context = error_retriever(err)
                        if error_context:
                            print(f"Retrieved error context: {len(error_context)} chars")
                    except Exception as retrieve_err:
                        print(f"Failed to retrieve error context: {retrieve_err}")

                try:
                    final_code = self.fix_code(final_code, err, error_context=error_context or "")
                except Exception as fix_err:
                    status = self._format_status("Fix failed", str(fix_err))
                    return final_code, status, None, False

                code_to_run = final_code + export_logic
                exec_success, out, err = self.kernel.run_code(code_to_run, working_dir, script_filename)

            if exec_success:
                status = "Success"
                success = True
                if stl_path.exists():
                    with open(stl_path, "rb") as f:
                        stl_binary = f.read()
                else:
                    stl_files = list(working_dir.glob("*.stl"))
                    if stl_files:
                        with open(stl_files[0], "rb") as f:
                            stl_binary = f.read()
                    else:
                        status = "Success (No STL)"
            else:
                status = self._format_status("Failed", err)

        except Exception as e:
            status = self._format_status("Error", str(e))
            print(f"Pipeline error: {e}")

        return final_code, status, stl_binary, success  # type: ignore[return-value]

    def run_generation_with_context(
        self,
        working_dir: Path,
        prompt: str,
        experiment_name: str,
        context_pack_str: str,
        rag_system_instruction: Optional[str] = None,
        do_fix: bool = True,
        error_retriever: Optional[Callable[[str], str]] = None,
    ) -> Tuple[str, str, Optional[bytes], bool]:
        """
        RAG-augmented generation: prepends retrieved documentation context
        to the prompt, then runs the standard generation -> execution -> fix loop.
        """
        from textwrap import dedent

        augmented_prompt = dedent(
            f"""\
            ## Relevant CadQuery Documentation
            The following documentation snippets are retrieved for reference.
            Use these for correct API usage and patterns.

            {context_pack_str}

            ---

            ## Task
            You will be given a natural language description of a 3D object.
            Your task is to generate runnable CadQuery code for that object.

            # Natural language description:
            {prompt}

            Now, write the corresponding CadQuery code following the JSON format exactly.
            The code_lines must be valid Python, import cadquery as cq, and assign the final CadQuery Workplane/Solid to a variable named result.
            """
        )

        try:
            result = self.run_generation_pipeline(
                working_dir=working_dir,
                prompt=augmented_prompt,
                experiment_name=experiment_name,
                do_fix=do_fix,
                error_retriever=error_retriever,
                system_instruction=rag_system_instruction,
                prompt_preformatted=True,
            )
        except Exception:
            raise

        return result

    def run_generation_pipeline(
        self,
        working_dir: Path,
        prompt: str,
        experiment_name: str,
        do_fix: bool = True,
        error_retriever: Optional[Callable[[str], str]] = None,
        system_instruction: Optional[str] = None,
        prompt_preformatted: bool = False,
    ) -> Tuple[str, str, Optional[bytes], bool]:
        """
        Runs the full generation -> execution -> fix loop.
        Returns (final_code, status, stl_binary, success)
        """
        effective_instruction = system_instruction or self.generation_config.get("expert_instruction")
        try:
            raw_response = self.generate_code_raw(prompt, effective_instruction, preformatted=prompt_preformatted)
            return self.execute_generated_response(
                working_dir=working_dir,
                raw_response=raw_response,
                experiment_name=experiment_name,
                do_fix=do_fix,
                error_retriever=error_retriever,
            )

        except Exception as e:
            status = self._format_status("Error", str(e))
            print(f"Pipeline error: {e}")
            return "", status, None, False
