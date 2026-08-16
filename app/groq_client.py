from __future__ import annotations

import asyncio
import re
import time
from typing import Dict, List

import httpx

from app.config import settings


_GROQ_SEMAPHORE = asyncio.Semaphore(settings.groq_max_concurrent_requests)


def _messages(system_prompt: str, history: List[Dict], user_message: str) -> List[Dict]:
    messages = [{"role": "system", "content": system_prompt[:settings.max_system_chars]}]
    per_turn_cap = settings.max_history_chars_per_turn
    for item in (history or [])[-settings.max_history_turns:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()[:per_turn_cap]})
    messages.append({"role": "user", "content": user_message.strip()[:settings.max_user_chars]})
    return messages


def _retry_seconds(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("retry-after") or response.headers.get("x-ratelimit-reset-tokens") or response.headers.get("x-ratelimit-reset-requests")
    if header:
        value = header.strip().lower()
        match = re.fullmatch(r"(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?", value)
        if match and (match.group(1) or match.group(2)):
            minutes = float(match.group(1) or 0)
            seconds = float(match.group(2) or 0)
            return min(settings.groq_max_backoff_seconds, max(0.0, minutes * 60 + seconds))
        try:
            return min(settings.groq_max_backoff_seconds, max(0.0, float(value)))
        except ValueError:
            pass
    return min(settings.groq_max_backoff_seconds, 0.75 * (2 ** attempt))


def _rate_limit_message(response: httpx.Response) -> str:
    retry_after = response.headers.get("retry-after") or response.headers.get("x-ratelimit-reset-tokens") or response.headers.get("x-ratelimit-reset-requests")
    if retry_after:
        return f"Groq is temporarily rate-limited. Please try again in about {retry_after.strip()}."
    return "Groq is temporarily rate-limited. Please try again shortly."


async def _request(model: str, messages: List[Dict]) -> httpx.Response:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": settings.temperature,
        "top_p": 0.92,
        "max_tokens": settings.max_response_tokens,
    }
    headers = {"Authorization": f"Bearer {settings.groq_token}", "Content-Type": "application/json"}
    timeout = httpx.Timeout(connect=10, read=90, write=30, pool=10)
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.post(settings.groq_url, json=payload, headers=headers)


async def _call_model(model: str, messages: List[Dict]) -> httpx.Response:
    last: httpx.Response | None = None
    for attempt in range(settings.groq_retry_attempts + 1):
        try:
            async with _GROQ_SEMAPHORE:
                response = await _request(model, messages)
        except httpx.TimeoutException as exc:
            raise RuntimeError("Groq API request timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise RuntimeError("Unable to connect to Groq API. Please try again.") from exc
        last = response
        if response.status_code != 429:
            return response
        if attempt < settings.groq_retry_attempts:
            await asyncio.sleep(_retry_seconds(response, attempt))
    assert last is not None
    return last


async def call_groq_detailed(system_prompt: str, history: List[Dict], user_message: str) -> dict:
    if not settings.groq_token:
        raise RuntimeError("GROQ_TOKEN is not set.")
    messages = _messages(system_prompt, history, user_message)
    models = [settings.groq_model]
    if settings.groq_enable_fallback and settings.groq_fallback_model and settings.groq_fallback_model != settings.groq_model:
        models.append(settings.groq_fallback_model)

    started = time.perf_counter()
    last_response: httpx.Response | None = None
    selected_model = models[0]
    for index, model in enumerate(models):
        response = await _call_model(model, messages)
        last_response = response
        selected_model = model
        if response.status_code == 429 and index < len(models) - 1:
            continue
        break

    assert last_response is not None
    response = last_response
    if response.status_code != 200:
        if response.status_code == 429:
            raise RuntimeError(_rate_limit_message(response))
        if response.status_code in (401, 403):
            raise RuntimeError("Groq API authentication failed. Check GROQ_TOKEN.")
        if response.status_code == 413:
            raise RuntimeError("Groq request was too large. TeluAI needs less conversation/context for this request.")
        raise RuntimeError(f"Groq API request failed ({response.status_code}).")

    try:
        data = response.json()
        choice = data["choices"][0]
        answer = str(choice["message"]["content"] or "").strip()
        usage = data.get("usage") or {}
        return {
            "answer": answer,
            "model": data.get("model", selected_model),
            "input_tokens": usage.get("prompt_tokens") or usage.get("input_tokens"),
            "output_tokens": usage.get("completion_tokens") or usage.get("output_tokens"),
            "finish_reason": choice.get("finish_reason"),
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    except Exception as exc:
        raise RuntimeError("Groq returned an invalid response.") from exc


async def call_groq(system_prompt: str, history: List[Dict], user_message: str) -> str:
    result = await call_groq_detailed(system_prompt, history, user_message)
    answer = result["answer"]
    if not answer:
        raise RuntimeError("Groq returned an empty response.")
    return answer
