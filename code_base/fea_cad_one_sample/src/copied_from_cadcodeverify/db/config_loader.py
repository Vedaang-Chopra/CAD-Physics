# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/utils/config_loader.py
from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

import yaml


DEFAULT_DB_CONNECTION_STRING = (
    "postgresql://vlmrouter:vlmrouter@localhost:5432/cadcode_verify_db"
)
DEFAULT_VARIANT = "baseline"

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_WRAPPER_KEYS = {"extends", "variant", "deprecated", "deprecation_message"}


def load_config(
    config_path: str | Path,
    variant: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load a config file and return a normalized, compatibility-first dict.

    Supported inputs:
    - Legacy YAMLs with db_connection_string/models/base_table_name.
    - New v2 YAMLs with db/model/variants.
    - Thin wrappers using `extends: <base-config>` + `variant: rag`.

    Returned configs expose the normalized shape:
        db.connection_string
        model.{id,slug,provider,connection_string,api_key}
        generation, evaluation, analysis, rag
        variant.{name,generation_table,model_name,pipeline_variant,table_name,table_ref}

    Legacy aliases are also populated:
        db_connection_string, base_table_name, models, analysis.table_name
    """
    path = Path(config_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw_config = _read_yaml(path)

    if "extends" in raw_config:
        base_path = (path.parent / raw_config["extends"]).expanduser()
        selected_variant = variant or raw_config.get("variant") or _infer_variant_from_path(path)
        normalized = load_config(
            base_path,
            variant=selected_variant,
            model_name=model_name,
        )

        wrapper_overrides = {
            key: value for key, value in raw_config.items() if key not in _WRAPPER_KEYS
        }
        if wrapper_overrides:
            normalized = _deep_merge(normalized, _expand_env_vars(wrapper_overrides))

        normalized["source_path"] = str(path)
        normalized["resolved_from"] = str(base_path)
        return normalized

    selected_variant = variant or raw_config.get("variant") or _infer_variant_from_path(path)
    if _is_v2_config(raw_config):
        normalized = _normalize_v2_config(raw_config, selected_variant, model_name)
    else:
        normalized = _normalize_legacy_config(raw_config, selected_variant, model_name)

    normalized["source_path"] = str(path)
    return normalized


def _read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config must contain a YAML mapping: {path}")

    return _expand_env_vars(data)


def _expand_env_vars(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    if isinstance(value, str):
        return _ENV_PATTERN.sub(
            lambda match: os.environ.get(match.group(1), match.group(0)),
            value,
        )
    return value


def _infer_variant_from_path(config_path: Path) -> str:
    stem = config_path.stem.lower()
    if stem.endswith("_rag"):
        return "rag"
    return DEFAULT_VARIANT


def _is_v2_config(config: Mapping[str, Any]) -> bool:
    return (
        config.get("version") == 2
        or "db" in config
        or "model" in config
        or "variants" in config
    )


def _normalize_v2_config(
    raw_config: Mapping[str, Any],
    variant_name: str,
    model_name: Optional[str],
) -> Dict[str, Any]:
    db_cfg = copy.deepcopy(raw_config.get("db", {}))
    if not isinstance(db_cfg, dict):
        db_cfg = {}

    generation_cfg = copy.deepcopy(raw_config.get("generation", {})) or {}
    evaluation_cfg = copy.deepcopy(raw_config.get("evaluation", {})) or {}
    base_analysis_cfg = copy.deepcopy(raw_config.get("analysis", {})) or {}
    base_model_cfg = copy.deepcopy(raw_config.get("model", {})) or {}
    raw_models = copy.deepcopy(raw_config.get("models", [])) or []
    variants_cfg = copy.deepcopy(raw_config.get("variants", {})) or {}

    if not variants_cfg:
        variants_cfg = {DEFAULT_VARIANT: {}}
    elif DEFAULT_VARIANT not in variants_cfg:
        variants_cfg[DEFAULT_VARIANT] = {}

    if variant_name not in variants_cfg:
        variant_name = DEFAULT_VARIANT

    variant_cfg = copy.deepcopy(variants_cfg.get(variant_name, {})) or {}
    if not isinstance(variant_cfg, dict):
        variant_cfg = {}

    if variant_cfg.get("generation"):
        generation_cfg = _deep_merge(generation_cfg, variant_cfg["generation"])
    if variant_cfg.get("evaluation"):
        evaluation_cfg = _deep_merge(evaluation_cfg, variant_cfg["evaluation"])

    selected_model_cfg = _select_model_config(raw_models, model_name)
    model_cfg = _deep_merge(base_model_cfg, selected_model_cfg)
    variant_model_cfg = variant_cfg.get("model") or {}
    if variant_model_cfg:
        model_cfg = _deep_merge(model_cfg, variant_model_cfg)

    model_id = model_cfg.get("id") or model_cfg.get("name") or model_name
    if not model_id:
        raise ValueError("Config is missing model.id/model.name and no model_name override was provided.")

    if "id" in variant_model_cfg and "slug" not in variant_model_cfg:
        model_slug = _slugify_identifier(model_id)
    else:
        model_slug = model_cfg.get("slug") or _slugify_identifier(model_id)
    provider = _normalize_provider(model_cfg.get("provider", "openai"), model_cfg.get("connection_string"))
    connection_string = model_cfg.get("connection_string")
    api_key = model_cfg.get("api_key")

    variant_base_table_name = (
        variant_cfg.get("base_table_name")
        or model_cfg.get("base_table_name")
        or raw_config.get("base_table_name")
        or model_slug
    )
    generation_table = variant_cfg.get("generation_table") or "model_generations"
    pipeline_variant = (
        variant_cfg.get("pipeline_variant")
        or ("baseline" if variant_name == DEFAULT_VARIANT else _slugify_identifier(variant_name))
    )
    canonical_model_name = (
        variant_cfg.get("model_name")
        or variant_cfg.get("generation_model_name")
        or variant_base_table_name
        or model_slug
    )

    if "model_name" in variant_cfg or "pipeline_variant" in variant_cfg:
        variant_table_ref = _compose_generation_target_ref(canonical_model_name, pipeline_variant)
    else:
        variant_table_ref = _resolve_generation_table_ref(
            table_name=variant_cfg.get("table_name"),
            base_table_name=variant_base_table_name,
            model_id=model_id,
        )
        canonical_model_name, pipeline_variant = _parse_generation_target_ref(variant_table_ref)

    variant_table_name = _sanitize_generation_table_name(variant_table_ref)

    rag_cfg = copy.deepcopy(variant_cfg.get("rag", {})) or {}
    if variant_name == "rag" and "enabled" not in variant_cfg:
        rag_enabled = True
    else:
        rag_enabled = bool(variant_cfg.get("enabled", variant_name == "rag"))

    analysis_cfg = _normalize_analysis_config(
        _deep_merge(base_analysis_cfg, variant_cfg.get("analysis", {})),
        fallback_model_id=model_id,
        fallback_provider=provider,
        fallback_connection_string=connection_string,
        fallback_api_key=api_key,
        fallback_table_name=variant_table_name,
    )
    analysis_cfg.update(
        {
            "generation_table": generation_table,
            "generation_model_name": canonical_model_name,
            "pipeline_variant": pipeline_variant,
        }
    )

    normalized_models = []
    source_models = raw_models if raw_models else [model_cfg]
    for model_entry in source_models:
        entry = _deep_merge(base_model_cfg, model_entry)
        if variant_model_cfg:
            entry = _deep_merge(entry, variant_model_cfg)
        entry_model_id = entry.get("id") or entry.get("name") or model_id
        entry_connection = entry.get("connection_string", connection_string)
        entry_provider = _normalize_provider(
            entry.get("provider", provider),
            entry_connection,
        )
        entry_api_key = entry.get("api_key", api_key)
        if "id" in variant_model_cfg and "slug" not in variant_model_cfg:
            entry_slug = _slugify_identifier(entry_model_id)
        else:
            entry_slug = entry.get("slug") or _slugify_identifier(entry_model_id)
        if "model_name" in variant_cfg or "pipeline_variant" in variant_cfg:
            entry_table_ref = variant_table_ref
            entry_generation_model_name = canonical_model_name
            entry_pipeline_variant = pipeline_variant
        else:
            entry_table_ref = _resolve_generation_table_ref(
                table_name=entry.get("table_name") or variant_cfg.get("table_name"),
                base_table_name=(
                    entry.get("base_table_name")
                    or variant_cfg.get("base_table_name")
                    or entry_slug
                ),
                model_id=entry_model_id,
            )
            entry_generation_model_name, entry_pipeline_variant = _parse_generation_target_ref(entry_table_ref)
        normalized_models.append(
            {
                "name": entry_model_id,
                "provider": entry_provider,
                "connection_string": entry_connection,
                "api_key": entry_api_key,
                "slug": entry_slug,
                "generation_table": generation_table,
                "generation_model_name": entry_generation_model_name,
                "pipeline_variant": entry_pipeline_variant,
                # Compatibility aliases consumed as logical generation targets,
                # not physical table names.
                "table_name": entry_table_ref,
                "base_table_name": entry_table_ref,
            }
        )

    normalized = {
        "version": 2,
        "db": {
            "connection_string": _resolve_db_connection_string(
                db_cfg.get("connection_string") or raw_config.get("db_connection_string")
            )
        },
        "model": {
            "id": model_id,
            "slug": model_slug,
            "provider": provider,
            "connection_string": connection_string,
            "api_key": api_key,
        },
        "generation": generation_cfg,
        "evaluation": evaluation_cfg,
        "analysis": analysis_cfg,
        "computation_graph": _normalize_computation_graph_config(raw_config.get("computation_graph")),
        "variants": variants_cfg,
        "variant": {
            "name": variant_name,
            "enabled": rag_enabled if variant_name == "rag" else True,
            "generation_table": generation_table,
            "model_name": canonical_model_name,
            "pipeline_variant": pipeline_variant,
            "base_table_name": variant_table_ref,
            "table_name": variant_table_name,
            "table_ref": variant_table_ref,
            "rag": rag_cfg,
        },
        "rag": rag_cfg,
        "models": normalized_models,
        "db_connection_string": _resolve_db_connection_string(
            db_cfg.get("connection_string") or raw_config.get("db_connection_string")
        ),
        "base_table_name": variant_table_ref,
    }

    return normalized


def _normalize_legacy_config(
    raw_config: Mapping[str, Any],
    variant_name: str,
    model_name: Optional[str],
) -> Dict[str, Any]:
    raw_models = copy.deepcopy(raw_config.get("models", [])) or []
    if not raw_models:
        raise ValueError("Legacy config is missing a non-empty `models` list.")

    selected_model_cfg = _select_model_config(raw_models, model_name)
    selected_model_id = selected_model_cfg.get("name") or model_name
    if not selected_model_id:
        raise ValueError("Legacy config model entry is missing `name`.")

    selected_connection = selected_model_cfg.get("connection_string")
    selected_provider = _normalize_provider(
        selected_model_cfg.get("provider", "openai"),
        selected_connection,
    )
    selected_slug = _slugify_identifier(selected_model_id)

    analysis_cfg = _normalize_analysis_config(
        raw_config.get("analysis", {}),
        fallback_model_id=selected_model_id,
        fallback_provider=selected_provider,
        fallback_connection_string=selected_connection,
        fallback_api_key=selected_model_cfg.get("api_key"),
        fallback_table_name=None,
    )

    table_from_analysis = analysis_cfg.get("table_name")
    raw_variant_table_name = None
    if variant_name == "rag":
        raw_variant_table_name = selected_model_cfg.get("table_name") or table_from_analysis
    elif len(raw_models) == 1:
        raw_variant_table_name = selected_model_cfg.get("table_name") or table_from_analysis

    if len(raw_models) == 1:
        variant_table_ref = _resolve_generation_table_ref(
            table_name=raw_variant_table_name,
            base_table_name=raw_config.get("base_table_name") or selected_slug,
            model_id=selected_model_id,
        )
    else:
        variant_table_ref = _resolve_generation_table_ref(
            table_name=raw_variant_table_name,
            base_table_name=selected_slug,
            model_id=selected_model_id,
        )

    variant_table_name = _resolve_generation_table_name(
        table_name=table_from_analysis or raw_variant_table_name,
        base_table_name=variant_table_ref,
        model_id=selected_model_id,
    )
    analysis_cfg["table_name"] = variant_table_name

    normalized_models = []
    for model_entry in raw_models:
        entry_name = model_entry.get("name")
        if not entry_name:
            continue
        entry_connection = model_entry.get("connection_string")
        entry_slug = _slugify_identifier(entry_name)
        entry_table_name = model_entry.get("table_name")
        entry_base_table_name = model_entry.get("base_table_name")
        if len(raw_models) == 1:
            entry_table_name = entry_table_name or analysis_cfg.get("table_name")
            entry_base_table_name = entry_base_table_name or raw_config.get("base_table_name")
        else:
            entry_base_table_name = entry_base_table_name or entry_slug
        entry_table_ref = _resolve_generation_table_ref(
            table_name=entry_table_name,
            base_table_name=entry_base_table_name,
            model_id=entry_name,
        )
        normalized_models.append(
            {
                "name": entry_name,
                "provider": _normalize_provider(
                    model_entry.get("provider", selected_provider),
                    entry_connection,
                ),
                "connection_string": entry_connection,
                "api_key": model_entry.get("api_key"),
                "slug": entry_slug,
                "table_name": entry_table_ref,
                "base_table_name": entry_table_ref,
            }
        )

    rag_cfg = copy.deepcopy(raw_config.get("rag", {})) or {}
    normalized = {
        "version": 1,
        "db": {
            "connection_string": _resolve_db_connection_string(
                raw_config.get("db_connection_string")
            )
        },
        "model": {
            "id": selected_model_id,
            "slug": selected_slug,
            "provider": selected_provider,
            "connection_string": selected_connection,
            "api_key": selected_model_cfg.get("api_key"),
        },
        "generation": copy.deepcopy(raw_config.get("generation", {})) or {},
        "evaluation": copy.deepcopy(raw_config.get("evaluation", {})) or {},
        "analysis": analysis_cfg,
        "computation_graph": _normalize_computation_graph_config(raw_config.get("computation_graph")),
        "variants": {
            variant_name: {
                "enabled": variant_name == "rag",
                "base_table_name": variant_table_ref,
                "table_name": variant_table_name,
                "rag": rag_cfg,
            }
        },
        "variant": {
            "name": variant_name,
            "enabled": variant_name == "rag" or variant_name == DEFAULT_VARIANT,
            "base_table_name": variant_table_ref,
            "table_name": variant_table_name,
            "table_ref": variant_table_ref,
            "rag": rag_cfg,
        },
        "rag": rag_cfg,
        "models": normalized_models,
        "db_connection_string": _resolve_db_connection_string(
            raw_config.get("db_connection_string")
        ),
        "base_table_name": variant_table_ref,
    }
    return normalized


def _normalize_analysis_config(
    raw_analysis: Optional[Mapping[str, Any]],
    *,
    fallback_model_id: str,
    fallback_provider: str,
    fallback_connection_string: Optional[str],
    fallback_api_key: Optional[str],
    fallback_table_name: Optional[str],
) -> Dict[str, Any]:
    analysis_cfg = copy.deepcopy(raw_analysis) if isinstance(raw_analysis, Mapping) else {}

    classifier_model_name = (
        analysis_cfg.get("classifier_model_name")
        or analysis_cfg.get("model_name")
        or fallback_model_id
    )
    classifier_connection_string = (
        analysis_cfg.get("classifier_connection_string")
        or analysis_cfg.get("connection_string")
        or fallback_connection_string
    )
    classifier_provider = _normalize_provider(
        analysis_cfg.get("classifier_provider")
        or analysis_cfg.get("provider")
        or fallback_provider,
        classifier_connection_string,
    )
    classifier_api_key = (
        analysis_cfg.get("classifier_api_key")
        if "classifier_api_key" in analysis_cfg
        else analysis_cfg.get("api_key", fallback_api_key)
    )

    table_name = analysis_cfg.get("table_name") or fallback_table_name
    if table_name:
        table_name = _resolve_generation_table_name(
            table_name=table_name,
            base_table_name=None,
            model_id=fallback_model_id,
        )

    analysis_cfg.update(
        {
            "classifier_model_name": classifier_model_name,
            "classifier_provider": classifier_provider,
            "classifier_connection_string": classifier_connection_string,
            "classifier_api_key": classifier_api_key,
            "model_name": classifier_model_name,
            "provider": classifier_provider,
            "connection_string": classifier_connection_string,
            "api_key": classifier_api_key,
            "table_name": table_name,
        }
    )
    return analysis_cfg


def _resolve_db_connection_string(connection_string: Optional[str]) -> str:
    if not connection_string or (
        isinstance(connection_string, str)
        and _ENV_PATTERN.search(connection_string)
    ):
        return os.environ.get(
            "CAD_DB_CONNECTION_STRING",
            DEFAULT_DB_CONNECTION_STRING,
        )
    return str(connection_string)


def _resolve_generation_table_name(
    *,
    table_name: Optional[str],
    base_table_name: Optional[str],
    model_id: Optional[str],
) -> str:
    if table_name:
        return _sanitize_generation_table_name(table_name)
    if base_table_name:
        return _sanitize_generation_table_name(base_table_name)
    if model_id:
        return _sanitize_generation_table_name(model_id)
    raise ValueError("Unable to derive generation table name.")


def _resolve_generation_table_ref(
    *,
    table_name: Optional[str],
    base_table_name: Optional[str],
    model_id: Optional[str],
) -> str:
    if table_name:
        return _strip_generation_prefix(_slugify_identifier(table_name))
    if base_table_name:
        return _strip_generation_prefix(_slugify_identifier(base_table_name))
    if model_id:
        return _strip_generation_prefix(_slugify_identifier(model_id))
    raise ValueError("Unable to derive generation table reference.")


def _compose_generation_target_ref(model_name: str, pipeline_variant: str) -> str:
    model_ref = _strip_generation_prefix(_slugify_identifier(model_name))
    pipeline_ref = _slugify_identifier(pipeline_variant or DEFAULT_VARIANT)
    if not pipeline_ref or pipeline_ref == DEFAULT_VARIANT:
        return model_ref
    suffix = f"_{pipeline_ref}"
    return model_ref if model_ref.endswith(suffix) else f"{model_ref}{suffix}"


def _parse_generation_target_ref(table_ref: str) -> tuple[str, str]:
    slug = _strip_generation_prefix(_slugify_identifier(table_ref))
    suffix_map = (
        ("_rag_rag_fixed", "rag_fixed"),
        ("_rag_fixed", "rag_fixed"),
        ("_rag_rag", "rag"),
        ("_rag", "rag"),
    )
    for suffix, pipeline_variant in suffix_map:
        if slug.endswith(suffix):
            return slug[: -len(suffix)], pipeline_variant
    return slug, DEFAULT_VARIANT


def _sanitize_generation_table_name(value: str) -> str:
    slug = _strip_generation_prefix(_slugify_identifier(value))
    return f"generations_{slug}" if slug else "generations"


def _strip_generation_prefix(value: str) -> str:
    if value.startswith("generations_"):
        return value[len("generations_") :]
    return value


def _slugify_identifier(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]", "_", str(value)).strip("_").lower()
    return re.sub(r"_+", "_", slug)


def _select_model_config(
    models: Iterable[Mapping[str, Any]],
    model_name: Optional[str],
) -> Dict[str, Any]:
    models_list = list(models or [])
    if not models_list:
        return {}
    if not model_name:
        return copy.deepcopy(models_list[0])

    target_slug = _slugify_identifier(model_name)
    for model_cfg in models_list:
        entry_name = model_cfg.get("id") or model_cfg.get("name")
        if entry_name == model_name:
            return copy.deepcopy(model_cfg)
        if entry_name and _slugify_identifier(entry_name) == target_slug:
            return copy.deepcopy(model_cfg)
        entry_slug = model_cfg.get("slug")
        if entry_slug and _slugify_identifier(entry_slug) == target_slug:
            return copy.deepcopy(model_cfg)

    return copy.deepcopy(models_list[0])


def _normalize_computation_graph_config(raw_cg: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """
    Normalize the computation_graph section for backward compatibility.

    Handles both old single-model format and new multi-model list format:
    - If raw_cg is None or empty, returns {"models": []}
    - If raw_cg["models"] exists and is a list, preserves as-is (new format)
    - If raw_cg["models"] exists and is a string/dict, wraps in a list
    - If raw_cg has no "models" key (old single-model format), wraps the
      entire dict as a single model entry and adds "models" key while keeping
      all original top-level fields

    Args:
        raw_cg: Raw computation_graph dict from YAML (may be None or empty)

    Returns:
        Normalized dict with guaranteed "models" field as list of dicts.
    """
    if not raw_cg:
        return {"models": []}

    normalized = copy.deepcopy(dict(raw_cg))
    models_field = normalized.get("models")

    # If models field exists and is already a list, keep as-is (new format)
    if isinstance(models_field, list):
        return normalized

    # If models field exists but is a string or dict, wrap in a list
    if models_field is not None:
        if isinstance(models_field, str):
            normalized["models"] = [{"model": models_field}]
        elif isinstance(models_field, dict):
            normalized["models"] = [models_field]
        else:
            # Unexpected type, default to empty
            normalized["models"] = []
        return normalized

    # If no models field exists (old single-model format):
    # Create a models list containing the entire config dict,
    # while keeping all original top-level fields as-is
    if normalized:
        normalized["models"] = [copy.deepcopy(dict(raw_cg))]
    else:
        normalized["models"] = []

    return normalized


def _normalize_provider(provider: Optional[str], connection_string: Optional[str]) -> str:
    normalized_provider = (provider or "openai").strip().lower()
    if normalized_provider == "vllm":
        return "openai"
    if normalized_provider == "ollama" and connection_string and ":11434" not in connection_string:
        return "openai"
    return normalized_provider


def _deep_merge(base: Mapping[str, Any], override: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    merged = copy.deepcopy(dict(base or {}))
    if not isinstance(override, Mapping):
        return merged
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], Mapping)
            and isinstance(value, Mapping)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged
