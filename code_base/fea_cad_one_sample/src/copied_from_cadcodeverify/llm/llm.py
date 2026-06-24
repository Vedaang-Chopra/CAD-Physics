# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/llm/llm.py
import os
import base64
import mimetypes
import re
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Generator, List, Union, Type
from pathlib import Path

# Try importing libraries and set flags/variables if they are missing
try:
    import openai
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from utils.config_loader import load_config as load_project_config
except ImportError:
    try:
        from code_base.utils.config_loader import load_config as load_project_config
    except ImportError:
        load_project_config = None

try:
    from utils.observability import langfuse_observation, summary_metadata_from_text
except ImportError:
    try:
        from code_base.utils.observability import langfuse_observation, summary_metadata_from_text
    except ImportError:
        langfuse_observation = None

        def summary_metadata_from_text(*, text: Optional[str], limit: int = 1200) -> str:
            value = "" if text is None else str(text)
            return value[:limit].rstrip() + "... [truncated]" if len(value) > limit else value

_ENV_PLACEHOLDER_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_API_ENV_PATH = Path(__file__).resolve().parents[2] / "api.env"
_API_ENV_CACHE: Optional[Dict[str, str]] = None

class ConnectorError(Exception):
    """Base exception for connector errors."""
    pass


@dataclass(frozen=True)
class LLMResponse:
    """Text response plus provider metadata for callers that need usage details."""

    content: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    raw_response: Any = None
    request_kwargs: Optional[Dict[str, Any]] = None


class _NoOpLLMObservation:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def update(self, **_: Any) -> None:
        return None


def _update_llm_observation(
    observation: Any,
    *,
    response: LLMResponse,
    duration_ms: int,
    retry_strategy: str,
) -> None:
    try:
        observation.update(
            output={
                "response_preview": summary_metadata_from_text(text=response.content),
                "finish_reason": response.finish_reason,
            },
            usage_details=response.usage or None,
            metadata={
                "duration_ms": duration_ms,
                "finish_reason": response.finish_reason,
                "retry_strategy": retry_strategy,
                "status": "success",
            },
        )
    except Exception:
        return None


def _update_llm_observation_error(
    observation: Any,
    *,
    error: BaseException,
    duration_ms: int,
    retry_strategy: str,
) -> None:
    try:
        observation.update(
            metadata={
                "duration_ms": duration_ms,
                "retry_strategy": retry_strategy,
                "status": "error",
                "error_type": type(error).__name__,
                "error": summary_metadata_from_text(text=str(error)),
            },
        )
    except Exception:
        return None


def _load_api_env_file() -> Dict[str, str]:
    """Load key/value pairs from code_base/api.env if present."""
    global _API_ENV_CACHE
    if _API_ENV_CACHE is not None:
        return _API_ENV_CACHE

    env_values: Dict[str, str] = {}
    if _API_ENV_PATH.exists():
        for raw_line in _API_ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and value:
                env_values[key] = value

    _API_ENV_CACHE = env_values
    return env_values

def encode_image(image_path: str) -> str:
    """Encodes a local image to base64."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        raise ConnectorError(f"Failed to encode image {image_path}: {e}")

class LLMConnector:
    """
    Unified connector for OpenAI-compatible LLM providers.
    
    Supported providers:
    - 'openai': Uses OpenAI API (default).
    - 'ollama': Uses OpenAI compatible API for Ollama.
    - Any other OpenAI-compatible provider via `connection_string`.
    """
    
    def __init__(self, model: str, provider: Optional[str] = "openai", api_key: Optional[str] = None, connection_string: Optional[str] = None, **kwargs):
        self.model = model
        self.api_key = api_key
        self.connection_string = connection_string
        self.provider = provider.lower() if provider else "openai"
        self.client_kwargs = kwargs
        
        self.client = self._initialize_client()

    def _initialize_client(self):
        if not HAS_OPENAI:
                raise ImportError("OpenAI library is not installed. Please install it with `pip install openai`.")
        
        # Default base_url for Ollama if not provided
        if self.provider == "ollama" and not self.connection_string:
            self.connection_string = "http://localhost:11434/v1"

        self.api_key = self._resolve_api_key_value(self.api_key)
        
        # API Key handling
        if not self.api_key:
            try:
                # Try to load API key from config.yaml if present
                config_path = Path("config/config.yaml")
                if config_path.exists() and load_project_config:
                    config_data = load_project_config(config_path)
                    for model_cfg in config_data.get("models", []):
                        if model_cfg.get("name") == self.model and "api_key" in model_cfg:
                            self.api_key = self._resolve_api_key_value(model_cfg["api_key"])
                            break
            except Exception:
                pass

        if not self.api_key:
            if self.provider == "openai":
                if self._uses_openrouter():
                    self.api_key = self._lookup_env_value(
                        "OPENROUTER_API_KEY",
                        "OPENROUTER_ENV",
                        "OPENAI_API_KEY",
                    )
                else:
                    self.api_key = self._lookup_env_value("OPENAI_API_KEY")
                if (
                    not self.api_key
                    and self.connection_string
                    and "api.openai.com" not in self.connection_string
                ):
                    self.api_key = "dummy"
            elif self.provider == "ollama":
                    self.api_key = "ollama" # Dummy key for Ollama
            else:
                self.api_key = "dummy" # Dummy key for other local providers
        
        # If connection_string is provided, use it as base_url
        base_url = self.connection_string if self.connection_string else None
        
        return OpenAI(api_key=self.api_key, base_url=base_url, **self.client_kwargs)

    def _lookup_env_value(self, *names: str) -> Optional[str]:
        env_file_values = _load_api_env_file()
        for name in names:
            value = os.environ.get(name) or env_file_values.get(name)
            if value:
                return value
        return None

    def _resolve_api_key_value(self, api_key: Optional[str]) -> Optional[str]:
        if api_key is None:
            return None
        if isinstance(api_key, str):
            stripped = api_key.strip()
            if not stripped:
                return None
            match = _ENV_PLACEHOLDER_PATTERN.match(stripped)
            if match:
                env_name = match.group(1)
                return self._lookup_env_value(env_name)
            return stripped
        return api_key

    def _uses_openrouter(self) -> bool:
        return bool(self.connection_string and "openrouter.ai" in self.connection_string.lower())

    def is_official_openai_endpoint(self) -> bool:
        """Return True only for the first-party OpenAI API endpoint."""
        if self.provider != "openai" or self._uses_openrouter():
            return False
        if not self.connection_string:
            return True
        return "api.openai.com" in self.connection_string.lower()

    def supports_batch_api(self) -> bool:
        """Whether this connector can use OpenAI's Batch API helpers below."""
        return self.is_official_openai_endpoint()

    def generate(self, prompt: str, system_instruction: Optional[str] = None, images: Optional[List[str]] = None, response_format: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return self.generate_with_metadata(
            prompt=prompt,
            system_instruction=system_instruction,
            images=images,
            response_format=response_format,
            **kwargs,
        ).content

    def generate_with_metadata(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        images: Optional[List[str]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> LLMResponse:
        create_kwargs = self.build_chat_completion_body(
            prompt=prompt,
            system_instruction=system_instruction,
            images=images,
            response_format=response_format,
            **kwargs,
        )

        def _call(call_kwargs):
            response = self.client.chat.completions.create(**call_kwargs)
            return LLMResponse(
                content=self._extract_chat_content(response),
                finish_reason=self._extract_finish_reason(response),
                usage=self._extract_usage(response),
                raw_response=response,
                request_kwargs=call_kwargs,
            )

        # Params that some newer OpenAI models reject — strip and retry on 400.
        _STRIPPABLE = ("temperature", "top_p", "presence_penalty", "frequency_penalty")

        observation_scope = (
            langfuse_observation(
                "llm.generate",
                as_type="generation",
                model=self.model,
                input_payload={
                    "prompt_preview": summary_metadata_from_text(text=prompt),
                    "system_instruction_preview": summary_metadata_from_text(
                        text=system_instruction,
                        limit=600,
                    ),
                    "image_count": len(images or []),
                    "response_format": bool(response_format),
                },
                metadata={
                    "provider": self.provider,
                    "model": self.model,
                    "official_openai_endpoint": self.is_official_openai_endpoint(),
                },
            )
            if langfuse_observation is not None
            else None
        )
        start_time = time.perf_counter()
        retry_strategy = "none"
        observation_cm = observation_scope if observation_scope is not None else _NoOpLLMObservation()
        try:
            with observation_cm as observation:
                try:
                    response = _call(create_kwargs)
                    _update_llm_observation(
                        observation,
                        response=response,
                        duration_ms=int((time.perf_counter() - start_time) * 1000),
                        retry_strategy=retry_strategy,
                    )
                    return response
                except ConnectorError as exc:
                    _update_llm_observation_error(
                        observation,
                        error=exc,
                        duration_ms=int((time.perf_counter() - start_time) * 1000),
                        retry_strategy=retry_strategy,
                    )
                    raise
                except Exception as e:
                    err_str = str(e)
                    if self._should_retry_without_prompt_cache_retention(create_kwargs, err_str):
                        retry_strategy = "without_prompt_cache_retention"
                        without_retention = dict(create_kwargs)
                        without_retention.pop("prompt_cache_retention", None)
                        try:
                            response = _call(without_retention)
                            _update_llm_observation(
                                observation,
                                response=response,
                                duration_ms=int((time.perf_counter() - start_time) * 1000),
                                retry_strategy=retry_strategy,
                            )
                            return response
                        except Exception as e2:
                            error = ConnectorError(f"{self.provider.capitalize()} generation failed: {e2}")
                            _update_llm_observation_error(
                                observation,
                                error=error,
                                duration_ms=int((time.perf_counter() - start_time) * 1000),
                                retry_strategy=retry_strategy,
                            )
                            raise error
                    if self.provider == "openai" and "400" in err_str:
                        stripped = {
                            key: value
                            for key, value in create_kwargs.items()
                            if key not in _STRIPPABLE or key not in err_str
                        }
                        if stripped != create_kwargs:
                            retry_strategy = "stripped_unsupported_params"
                            try:
                                response = _call(stripped)
                                _update_llm_observation(
                                    observation,
                                    response=response,
                                    duration_ms=int((time.perf_counter() - start_time) * 1000),
                                    retry_strategy=retry_strategy,
                                )
                                return response
                            except Exception as e2:
                                error = ConnectorError(f"{self.provider.capitalize()} generation failed: {e2}")
                                _update_llm_observation_error(
                                    observation,
                                    error=error,
                                    duration_ms=int((time.perf_counter() - start_time) * 1000),
                                    retry_strategy=retry_strategy,
                                )
                                raise error
                    error = ConnectorError(f"{self.provider.capitalize()} generation failed: {e}")
                    _update_llm_observation_error(
                        observation,
                        error=error,
                        duration_ms=int((time.perf_counter() - start_time) * 1000),
                        retry_strategy=retry_strategy,
                    )
                    raise error
        except ConnectorError:
            raise

    def build_chat_completion_body(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        images: Optional[List[str]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        messages = self._prepare_messages(prompt, system_instruction, images)
        kwargs = self._normalize_chat_kwargs(kwargs)
        create_kwargs = dict(model=self.model, messages=messages, **kwargs)
        if response_format:
            create_kwargs["response_format"] = response_format
        return create_kwargs

    def _normalize_chat_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(kwargs)
        # Newer OpenAI models (gpt-5-mini, o-series, etc.) require max_completion_tokens
        # instead of max_tokens. Remap transparently for the openai provider.
        if self.provider == "openai" and "max_tokens" in kwargs:
            normalized["max_completion_tokens"] = normalized.pop("max_tokens")

        if not self.is_official_openai_endpoint():
            normalized.pop("prompt_cache_key", None)
            normalized.pop("prompt_cache_retention", None)

        return normalized

    def build_batch_request(
        self,
        custom_id: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Build one JSONL request object for OpenAI Batch `/v1/chat/completions`."""
        self._require_official_openai("Batch API")
        body = self.build_chat_completion_body(
            prompt=prompt,
            system_instruction=system_instruction,
            response_format=response_format,
            **kwargs,
        )
        return {
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body,
        }

    def upload_batch_file(self, input_path: str | Path) -> str:
        self._require_official_openai("Batch API")
        with Path(input_path).open("rb") as handle:
            uploaded = self.client.files.create(file=handle, purpose="batch")
        return str(self._value(uploaded, "id"))

    def create_batch(
        self,
        input_file_id: str,
        *,
        completion_window: str = "24h",
        endpoint: str = "/v1/chat/completions",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Any:
        self._require_official_openai("Batch API")
        kwargs = {
            "input_file_id": input_file_id,
            "endpoint": endpoint,
            "completion_window": completion_window,
        }
        if metadata:
            kwargs["metadata"] = metadata
        return self.client.batches.create(**kwargs)

    def retrieve_batch(self, batch_id: str) -> Any:
        self._require_official_openai("Batch API")
        return self.client.batches.retrieve(batch_id)

    def download_file_text(self, file_id: str) -> str:
        self._require_official_openai("Files API")
        file_response = self.client.files.content(file_id)
        if hasattr(file_response, "text"):
            text_value = file_response.text
            return text_value() if callable(text_value) else text_value
        if hasattr(file_response, "read"):
            content = file_response.read()
            if isinstance(content, bytes):
                return content.decode("utf-8")
            return str(content)
        return str(file_response)

    def _require_official_openai(self, feature: str) -> None:
        if not self.is_official_openai_endpoint():
            raise ConnectorError(f"{feature} is only available for the official OpenAI API endpoint.")

    def _should_retry_without_prompt_cache_retention(
        self,
        request_kwargs: Dict[str, Any],
        error_text: str,
    ) -> bool:
        if not self.is_official_openai_endpoint():
            return False
        if "prompt_cache_retention" not in request_kwargs:
            return False
        lowered = (error_text or "").lower()
        return (
            "400" in lowered
            and "prompt_cache_retention" in lowered
            and any(marker in lowered for marker in ("unsupported", "unrecognized", "unknown", "invalid"))
        )

    @staticmethod
    def _should_retry_test_connection(error_text: str) -> bool:
        lowered = (error_text or "").lower()
        if not lowered:
            return False
        transient_markers = (
            "no healthy upstream",
            "temporarily unavailable",
            "temporarily overloaded",
            "connection error",
            "connection reset",
            "timed out",
            "timeout",
            "rate limit",
            "server error",
            "service unavailable",
            "bad gateway",
            "gateway timeout",
        )
        if any(marker in lowered for marker in transient_markers):
            return True
        return any(code in lowered for code in (" 502", " 503", " 504", "code: 502", "code: 503", "code: 504"))

    @staticmethod
    def _value(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @classmethod
    def _to_dict(cls, obj: Any) -> Optional[Dict[str, Any]]:
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        if hasattr(obj, "__dict__"):
            return {
                key: value
                for key, value in vars(obj).items()
                if not key.startswith("_")
            }
        return None

    @classmethod
    def _extract_chat_content(cls, response: Any) -> str:
        choices = cls._value(response, "choices", []) or []
        if not choices:
            return ""
        first_choice = choices[0]
        message = cls._value(first_choice, "message", {}) or {}
        content = cls._value(message, "content", "")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        content = content or ""
        reasoning_content = cls._value(message, "reasoning_content", "")
        if not content and reasoning_content:
            reasoning_text = str(reasoning_content).strip()
            if cls._looks_like_structured_assistant_output(reasoning_text):
                return reasoning_text
            finish_reason = cls._value(first_choice, "finish_reason", None)
            detail = (
                "Model returned reasoning_content but empty message.content"
                f" (finish_reason={finish_reason!r})."
            )
            if finish_reason == "length":
                detail += " The model exhausted the completion budget in reasoning before final answer."
            detail += " Increase max_tokens/max_completion_tokens and retry."
            raise ConnectorError(detail)
        return content

    @classmethod
    def _looks_like_structured_assistant_output(cls, text: str) -> bool:
        stripped = (text or "").strip()
        if not stripped:
            return False
        if stripped.startswith(("```", "{", "[")):
            return True
        return any(marker in stripped for marker in ('"code_lines"', '"code"', "import ", "cadquery", "cq."))

    @classmethod
    def _extract_finish_reason(cls, response: Any) -> Optional[str]:
        choices = cls._value(response, "choices", []) or []
        if not choices:
            return None
        return cls._value(choices[0], "finish_reason", None)

    @classmethod
    def _extract_usage(cls, response: Any) -> Optional[Dict[str, Any]]:
        usage = cls._value(response, "usage")
        return cls._to_dict(usage)

    def stream(self, prompt: str, system_instruction: Optional[str] = None, images: Optional[List[str]] = None, **kwargs) -> Generator[str, None, None]:
        messages = self._prepare_messages(prompt, system_instruction, images)
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
                raise ConnectorError(f"{self.provider.capitalize()} streaming failed: {e}")

    def test_connection(
        self,
        *,
        max_attempts: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> tuple:
        """
        Send a lightweight ping to verify the model is reachable.
        Returns (success: bool, message: str).
        """
        tokens_kwarg = "max_completion_tokens" if self.provider == "openai" else "max_tokens"
        max_attempts = max(1, int(max_attempts))
        last_error = ""

        for attempt in range(1, max_attempts + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Say hello in one word."}],
                    **{tokens_kwarg: 512},
                )
                reply = self._extract_chat_content(resp).strip()
                if not reply:
                    finish_reason = self._extract_finish_reason(resp)
                    last_error = f"Empty model response (finish_reason={finish_reason!r})."
                else:
                    return True, reply
            except ConnectorError as e:
                last_error = str(e)
            except Exception as e:
                last_error = str(e)

            if attempt < max_attempts and self._should_retry_test_connection(last_error):
                time.sleep(retry_delay_seconds)
                continue

            if attempt > 1 and self._should_retry_test_connection(last_error):
                return False, f"{last_error} (after {attempt} attempts)"
            return False, last_error

        return False, last_error or "Connection error."

    # --- Internal Implementation ---

    def _prepare_messages(self, prompt: str, system_instruction: Optional[str], images: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        
        content = [{"type": "text", "text": prompt}]
        
        if images:
            for img_path in images:
                base64_image = encode_image(img_path)
                mime_type, _ = mimetypes.guess_type(img_path)
                if not mime_type:
                    mime_type = "image/jpeg"
                
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}"
                    }
                })
        
        messages.append({"role": "user", "content": content})
        return messages
