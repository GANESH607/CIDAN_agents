import json
import logging
import re
from typing import Any, Literal, TypeVar, get_args

from langchain_groq import ChatGroq
from pydantic import BaseModel

from cidan.config import get_settings, require_llm_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def _sanitize_data_for_schema(data: Any, schema: type[BaseModel]) -> Any:
    """Clamps string lengths to schema bounds if the LLM generated slightly overlong text."""
    if not isinstance(data, dict):
        return data
    sanitized = dict(data)
    for key, field_info in schema.model_fields.items():
        if key not in sanitized or sanitized[key] is None:
            continue
        val = sanitized[key]

        # String field max_length check
        max_len = None
        for meta in field_info.metadata:
            if hasattr(meta, "max_length"):
                max_len = meta.max_length
                break
        if max_len is not None and isinstance(val, str) and len(val) > max_len:
            sanitized[key] = val[:max_len]

        # List items check
        if isinstance(val, list):
            # Check list length limit
            list_max = None
            for meta in field_info.metadata:
                if hasattr(meta, "max_length"):
                    list_max = meta.max_length
                    break
            if list_max is not None and len(val) > list_max:
                val = val[:list_max]

            # Check individual item max_length (e.g., ShortEvidence, ChunkId)
            item_max_len = None
            if key == "evidence_limitations":
                item_max_len = 100
            elif key == "cited_policy_chunk_ids":
                item_max_len = 64
            else:
                try:
                    args = get_args(field_info.annotation)
                    if args and hasattr(args[0], "__metadata__"):
                        for m in args[0].__metadata__:
                            if hasattr(m, "max_length"):
                                item_max_len = m.max_length
                                break
                            if hasattr(m, "metadata"):
                                for inner_m in m.metadata:
                                    if hasattr(inner_m, "max_length"):
                                        item_max_len = inner_m.max_length
                                        break
                except Exception:
                    pass

            if item_max_len is not None:
                val = [
                    item[:item_max_len] if isinstance(item, str) and len(item) > item_max_len else item
                    for item in val
                ]
            sanitized[key] = val
    return sanitized


def structured_llm(
    schema: type[T],
    max_tokens: int | None = None,
    *,
    method: Literal["json_schema", "json_mode"] = "json_schema",
    temperature: float = 0,
) -> Any:
    settings = require_llm_settings(get_settings())
    model = ChatGroq(
        model=settings.llm_model,
        groq_api_key=settings.groq_api_key,
        timeout=settings.llm_timeout_seconds,
        max_tokens=max_tokens or settings.llm_max_output_tokens,
        max_retries=2,
        temperature=temperature,
    )
    return model.with_structured_output(schema, method=method)


def invoke_structured(
    schema: type[T],
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int | None = None,
    method: Literal["json_schema", "json_mode"] = "json_schema",
    temperature: float = 0,
) -> T:
    runnable = structured_llm(
        schema,
        max_tokens=max_tokens,
        method=method,
        temperature=temperature,
    )
    try:
        return runnable.invoke([("system", system_prompt), ("human", user_prompt)])
    except Exception as exc:
        logger.warning(
            "Structured output validation failed for %s: %s. Attempting length sanitization...",
            schema.__name__,
            exc,
        )
        raw_text = getattr(exc, "llm_output", None)
        # Check if error message contains the JSON completion
        if not raw_text:
            msg = str(exc)
            m = re.search(r"completion\s+(\{.*?\})\.", msg, re.DOTALL)
            if m:
                raw_text = m.group(1)

        if not raw_text:
            try:
                settings = require_llm_settings(get_settings())
                direct_model = ChatGroq(
                    model=settings.llm_model,
                    groq_api_key=settings.groq_api_key,
                    timeout=settings.llm_timeout_seconds,
                    max_tokens=max_tokens or settings.llm_max_output_tokens,
                    max_retries=1,
                    temperature=temperature,
                )
                resp = direct_model.invoke([("system", system_prompt), ("human", user_prompt)])
                raw_text = resp.content
            except Exception:
                pass

        if raw_text:
            try:
                m_json = re.search(r"\{.*\}", str(raw_text), re.DOTALL)
                if m_json:
                    data = json.loads(m_json.group(0))
                    sanitized = _sanitize_data_for_schema(data, schema)
                    return schema.model_validate(sanitized)
            except Exception as inner_exc:
                logger.error("Failed to recover via schema sanitization: %s", inner_exc)

        logger.exception("LLM agent invocation failed for schema %s", schema.__name__)
        raise
