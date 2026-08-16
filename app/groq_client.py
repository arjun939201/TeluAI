from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import AsyncIterator
from typing import Dict, List

import httpx

from app.config import settings

_GROQ_SEMAPHORE = asyncio.Semaphore(settings.groq_max_concurrent_requests)
_CLIENT: httpx.AsyncClient | None = None
_CLIENT_LOCK = asyncio.Lock()


async def _client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        async with _CLIENT_LOCK:
            if _CLIENT is None or _CLIENT.is_closed:
                _CLIENT = httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=90, write=30, pool=10))
    return _CLIENT


def _messages(system_prompt: str, history: List[Dict], user_message: str) -> List[Dict]:
    messages = [{"role": "system", "content": system_prompt[:settings.max_system_chars]}]
    for item in (history or [])[-settings.max_history_turns:]:
        if not isinstance(item, dict):
            continue
        role, content = item.get("role"), item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()[:settings.max_history_chars_per_turn]})
    messages.append({"role": "user", "content": user_message.strip()[:settings.max_user_chars]})
    return messages


def _retry_seconds(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("retry-after") or response.headers.get("x-ratelimit-reset-tokens") or response.headers.get("x-ratelimit-reset-requests")
    if header:
        value = header.strip().lower()
        match = re.fullmatch(r"(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?", value)
        if match and (match.group(1) or match.group(2)):
            return min(settings.groq_max_backoff_seconds, float(match.group(1) or 0) * 60 + float(match.group(2) or 0))
        try:
            return min(settings.groq_max_backoff_seconds, max(0.0, float(value)))
        except ValueError:
            pass
    return min(settings.groq_max_backoff_seconds, 0.75 * (2 ** attempt))


def _friendly_error(status: int, response: httpx.Response | None = None) -> str:
    if status == 429:
        retry = (response.headers.get("retry-after") if response else None)
        return f"Too many requests right now. Please try again in {retry.strip()} seconds." if retry and retry.isdigit() else "Too many requests right now. Please try again in a moment."
    if status in (401, 403):
        return "AI service authentication is temporarily unavailable."
    if status == 413:
        return "This conversation is too large for the AI service. Try starting a new chat or shortening the request."
    if status >= 500:
        return "The AI service is temporarily unavailable. Please try again shortly."
    return "The AI service could not complete that request. Please try again."


async def _post(model: str, messages: List[Dict], *, stream: bool) -> httpx.Response:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": settings.temperature,
        "top_p": 0.92,
        "max_tokens": settings.max_response_tokens,
        "stream": stream,
    }
    headers = {"Authorization": f"Bearer {settings.groq_token}", "Content-Type": "application/json"}
    client = await _client()
    async with _GROQ_SEMAPHORE:
        return await client.post(settings.groq_url, json=payload, headers=headers)


async def _call_model(model: str, messages: List[Dict]) -> httpx.Response:
    last: httpx.Response | None = None
    for attempt in range(settings.groq_retry_attempts + 1):
        try:
            response = await _post(model, messages, stream=False)
        except httpx.TimeoutException as exc:
            raise RuntimeError("The AI service timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise RuntimeError("Unable to connect to the AI service. Please try again.") from exc
        last = response
        if response.status_code != 429:
            return response
        if attempt < settings.groq_retry_attempts:
            await asyncio.sleep(_retry_seconds(response, attempt))
    return last  # type: ignore[return-value]


async def call_groq_detailed(system_prompt: str, history: List[Dict], user_message: str) -> dict:
    if not settings.groq_token:
        raise RuntimeError("The AI service is not configured yet.")
    messages = _messages(system_prompt, history, user_message)
    models = [settings.groq_model]
    if settings.groq_enable_fallback and settings.groq_fallback_model and settings.groq_fallback_model != settings.groq_model:
        models.append(settings.groq_fallback_model)
    started = time.perf_counter()
    response = None
    selected_model = models[0]
    for i, model in enumerate(models):
        response = await _call_model(model, messages)
        selected_model = model
        if response.status_code == 429 and i < len(models) - 1:
            continue
        break
    assert response is not None
    if response.status_code != 200:
        raise RuntimeError(_friendly_error(response.status_code, response))
    try:
        data = response.json(); choice = data["choices"][0]
        answer = str(choice["message"]["content"] or "").strip(); usage = data.get("usage") or {}
        return {"answer": answer, "model": data.get("model", selected_model),
                "input_tokens": usage.get("prompt_tokens") or usage.get("input_tokens"),
                "output_tokens": usage.get("completion_tokens") or usage.get("output_tokens"),
                "finish_reason": choice.get("finish_reason"),
                "latency_ms": int((time.perf_counter() - started) * 1000)}
    except Exception as exc:
        raise RuntimeError("The AI service returned an invalid response.") from exc


async def stream_groq(system_prompt: str, history: List[Dict], user_message: str) -> AsyncIterator[dict]:
    """Yield OpenAI-compatible Groq stream events as normalized dictionaries."""
    if not settings.groq_token:
        raise RuntimeError("The AI service is not configured yet.")
    messages = _messages(system_prompt, history, user_message)
    models = [settings.groq_model]
    if settings.groq_enable_fallback and settings.groq_fallback_model and settings.groq_fallback_model != settings.groq_model:
        models.append(settings.groq_fallback_model)

    last_error = None
    for model_index, model in enumerate(models):
        started = time.perf_counter()
        try:
            client = await _client()
            payload = {"model": model, "messages": messages, "temperature": settings.temperature,
                       "top_p": 0.92, "max_tokens": settings.max_response_tokens, "stream": True}
            headers = {"Authorization": f"Bearer {settings.groq_token}", "Content-Type": "application/json"}
            async with _GROQ_SEMAPHORE:
                async with client.stream("POST", settings.groq_url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        last_error = _friendly_error(response.status_code, response)
                        if response.status_code == 429 and model_index < len(models) - 1:
                            await response.aread(); continue
                        raise RuntimeError(last_error)
                    yield {"type": "start", "model": model}
                    input_tokens = output_tokens = None
                    finish_reason = None
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        usage = data.get("usage") or {}
                        input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or input_tokens
                        output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or output_tokens
                        for choice in data.get("choices") or []:
                            finish_reason = choice.get("finish_reason") or finish_reason
                            delta = choice.get("delta") or {}
                            text = delta.get("content")
                            if text:
                                yield {"type": "delta", "text": str(text)}
                    yield {"type": "done", "model": model, "input_tokens": input_tokens,
                           "output_tokens": output_tokens, "finish_reason": finish_reason,
                           "latency_ms": int((time.perf_counter() - started) * 1000)}
                    return
        except asyncio.CancelledError:
            raise
        except (httpx.TimeoutException,) as exc:
            raise RuntimeError("The AI service timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise RuntimeError("Unable to connect to the AI service. Please try again.") from exc
    raise RuntimeError(last_error or "The AI service could not complete that request.")


async def call_groq(system_prompt: str, history: List[Dict], user_message: str) -> str:
    result = call_groq_detailed
    data = await result(system_prompt, history, user_message)
    if not data["answer"]:
        raise RuntimeError("The AI service returned an empty response.")
    return data["answer"]
