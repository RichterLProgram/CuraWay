from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from src.ai.openai_client import DEFAULT_OPENAI_MODEL, get_openai_client
from src.observability.trace_store import record_llm_call

try:
    from anthropic import Anthropic  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Anthropic = None

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass
class LlmResult:
    text: str
    parsed: Optional[Any]
    model: str
    provider: str
    usage: Dict[str, Any]
    latency_ms: int


def call_llm(
    prompt: str,
    schema: Optional[Type[ModelT] | Dict[str, Any]] = None,
    temperature: Optional[float] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    trace_id: Optional[str] = None,
    step_id: Optional[str] = None,
    input_refs: Optional[Dict[str, Any]] = None,
    output_claims: Optional[Dict[str, Any]] = None,
    mock_key: Optional[str] = None,
) -> LlmResult:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    trace_id = trace_id or str(uuid.uuid4())
    step_id = step_id or str(uuid.uuid4())
    temperature = 0.2 if temperature is None else temperature

    if os.getenv("LLM_DISABLED", "false").lower() == "true":
        result = _load_mock_response(prompt, schema, mock_key=mock_key)
        record_llm_call(
            trace_id=trace_id,
            step_id=step_id,
            provider="mock",
            model="mock",
            prompt=prompt,
            response_text=result.text,
            usage={"mock": True},
            latency_ms=0,
            input_refs=input_refs,
            output_claims=output_claims or _claims_from_parsed(result.parsed),
        )
        return result

    if provider == "claude":
        return _call_claude(
            prompt=prompt,
            schema=schema,
            temperature=temperature,
            model=model,
            system_prompt=system_prompt,
            trace_id=trace_id,
            step_id=step_id,
            input_refs=input_refs,
            output_claims=output_claims,
        )

    return _call_openai(
        prompt=prompt,
        schema=schema,
        temperature=temperature,
        model=model,
        system_prompt=system_prompt,
        trace_id=trace_id,
        step_id=step_id,
        input_refs=input_refs,
        output_claims=output_claims,
    )


def _call_openai(
    prompt: str,
    schema: Optional[Type[ModelT] | Dict[str, Any]],
    temperature: float,
    model: Optional[str],
    system_prompt: Optional[str],
    trace_id: str,
    step_id: str,
    input_refs: Optional[Dict[str, Any]],
    output_claims: Optional[Dict[str, Any]],
) -> LlmResult:
    client = get_openai_client()
    selected_model = model or DEFAULT_OPENAI_MODEL
    messages = _build_messages(prompt, system_prompt)
    start = time.perf_counter()
    response_text = ""
    usage: Dict[str, Any] = {}

    if schema is not None:
        schema_payload = _schema_for(schema)
        try:
            response = client.responses.create(
                model=selected_model,
                input=messages,
                temperature=temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": _schema_name(schema),
                        "schema": schema_payload,
                        "strict": True,
                    },
                },
            )
            response_text = _extract_response_text(response)
            usage = _extract_usage(response)
        except TypeError:
            response = client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            response_text = _extract_response_text(response)
            usage = _extract_usage(response)
    else:
        response = client.responses.create(
            model=selected_model,
            input=messages,
            temperature=temperature,
        )
        response_text = _extract_response_text(response)
        usage = _extract_usage(response)

    latency_ms = int((time.perf_counter() - start) * 1000)
    if not response_text:
        raise RuntimeError("LLM returned an empty response.")

    parsed = _parse_structured(schema, response_text) if schema is not None else None
    record_llm_call(
        trace_id=trace_id,
        step_id=step_id,
        provider="openai",
        model=selected_model,
        prompt=prompt,
        response_text=response_text,
        usage=usage,
        latency_ms=latency_ms,
        input_refs=input_refs,
        output_claims=output_claims or _claims_from_parsed(parsed),
    )
    return LlmResult(
        text=response_text,
        parsed=parsed,
        model=selected_model,
        provider="openai",
        usage=usage,
        latency_ms=latency_ms,
    )


def _call_claude(
    prompt: str,
    schema: Optional[Type[ModelT] | Dict[str, Any]],
    temperature: float,
    model: Optional[str],
    system_prompt: Optional[str],
    trace_id: str,
    step_id: str,
    input_refs: Optional[Dict[str, Any]],
    output_claims: Optional[Dict[str, Any]],
) -> LlmResult:
    if Anthropic is None:
        raise RuntimeError("Claude provider requested but anthropic is not installed.")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    client = Anthropic(api_key=api_key)
    selected_model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    start = time.perf_counter()

    system = system_prompt or ""
    if schema is not None:
        schema_block = json.dumps(_schema_for(schema), ensure_ascii=False)
        system = f"{system}\n\nReturn ONLY valid JSON for this schema:\n{schema_block}"

    response = client.messages.create(
        model=selected_model,
        system=system,
        temperature=temperature,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = ""
    if getattr(response, "content", None):
        response_text = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
    latency_ms = int((time.perf_counter() - start) * 1000)
    if not response_text:
        raise RuntimeError("LLM returned an empty response.")

    parsed = _parse_structured(schema, response_text) if schema is not None else None
    record_llm_call(
        trace_id=trace_id,
        step_id=step_id,
        provider="claude",
        model=selected_model,
        prompt=prompt,
        response_text=response_text,
        usage={"provider": "claude"},
        latency_ms=latency_ms,
        input_refs=input_refs,
        output_claims=output_claims or _claims_from_parsed(parsed),
    )
    return LlmResult(
        text=response_text,
        parsed=parsed,
        model=selected_model,
        provider="claude",
        usage={"provider": "claude"},
        latency_ms=latency_ms,
    )


def _build_messages(prompt: str, system_prompt: Optional[str]) -> list[Dict[str, str]]:
    if system_prompt:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
    return [{"role": "user", "content": prompt}]


def _schema_for(schema: Type[ModelT] | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(schema, dict):
        return schema
    return schema.model_json_schema()


def _schema_name(schema: Type[ModelT] | Dict[str, Any]) -> str:
    if isinstance(schema, dict):
        return "Schema"
    return schema.__name__


def _extract_response_text(response: Any) -> str:
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text
    if hasattr(response, "output") and response.output:
        content = response.output[0].content
        if content:
            first = content[0]
            if hasattr(first, "text"):
                return first.text or ""
    if hasattr(response, "choices") and response.choices:
        message = response.choices[0].message
        if message and hasattr(message, "content"):
            return message.content or ""
    return ""


def _extract_usage(response: Any) -> Dict[str, Any]:
    usage = getattr(response, "usage", None)
    if isinstance(usage, dict):
        return usage
    if usage is not None and hasattr(usage, "model_dump"):
        return usage.model_dump()
    return {}


def _strip_code_fences(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return text


def _extract_json_object(content: str) -> str:
    text = _strip_code_fences(content)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()
    return text


def _parse_structured(
    schema: Optional[Type[ModelT] | Dict[str, Any]],
    content: str,
) -> Optional[Any]:
    if schema is None:
        return None
    payload_text = _extract_json_object(content)
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid JSON returned by LLM.") from exc

    if isinstance(schema, dict):
        return payload

    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise RuntimeError("LLM response failed schema validation.") from exc


def _claims_from_parsed(parsed: Optional[Any]) -> Dict[str, Any]:
    if parsed is None:
        return {}
    if hasattr(parsed, "model_dump"):
        return parsed.model_dump()
    if isinstance(parsed, dict):
        return parsed
    return {"value": parsed}


def _load_mock_response(
    prompt: str,
    schema: Optional[Type[ModelT] | Dict[str, Any]],
    mock_key: Optional[str],
) -> LlmResult:
    key = mock_key or _schema_name(schema) if schema is not None else "text"
    fixtures_dir = os.getenv(
        "LLM_FIXTURE_DIR",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "tests",
            "fixtures",
            "llm",
        ),
    )
    path = os.path.join(fixtures_dir, f"{key}.json")
    if not os.path.exists(path):
        raise RuntimeError(f"LLM fixture not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    response_text = json.dumps(data, ensure_ascii=False)
    parsed = _parse_structured(schema, response_text) if schema is not None else None
    return LlmResult(
        text=response_text,
        parsed=parsed,
        model="mock",
        provider="mock",
        usage={"mock": True, "prompt_chars": len(prompt)},
        latency_ms=0,
    )
