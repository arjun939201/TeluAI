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


class GroqRateLimitError(RuntimeError):
    def __init__(self, retry_after_seconds: float = 60.0, message: str = "Too many requests right now. Please wait before trying again."):
        super().__init__(message)
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        self.code = "groq_rate_limit"
        self.retryable = True


class GroqProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, code: str = "groq_provider_error"):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.retryable = status_code is None or status_code >= 500


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
            numeric = float(value)
            # Reset headers can be epoch seconds.
            if numeric > time.time():
                return min(settings.groq_max_backoff_seconds, max(1.0, numeric - time.time()))
            return min(settings.groq_max_backoff_seconds, max(0.0, numeric))
        except ValueError:
            pass
    return min(settings.groq_max_backoff_seconds, 0.75 * (2 ** attempt))


def _retry_from_response(response: httpx.Response) -> float:
    value = response.headers.get("retry-after") or response.headers.get("x-ratelimit-reset-tokens") or response.headers.get("x-ratelimit-reset-requests")
    if value:
        text = value.strip().lower()
        match = re.fullmatch(r"(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?", text)
        if match and (match.group(1) or match.group(2)):
            return max(1.0, float(match.group(1) or 0) * 60 + float(match.group(2) or 0))
        try:
            numeric = float(text)
            return max(1.0, numeric - time.time()) if numeric > time.time() else max(1.0, numeric)
        except ValueError:
            pass
    return 60.0


def _provider_message(response: httpx.Response) -> str:
    try:
        data = response.json()
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:500]
        if isinstance(error, str) and error.strip():
            return error.strip()[:500]
        detail = data.get("detail") if isinstance(data, dict) else None
        if isinstance(detail, str) and detail.strip():
            return detail.strip()[:500]
    except Exception:
        pass
    return ""


def _friendly_error(status: int, response: httpx.Response | None = None) -> str:
    if status == 429:
        retry = _retry_from_response(response) if response is not None else 60.0
        raise GroqRateLimitError(retry, f"Too many requests right now. Please try again in {max(1, int(retry))} seconds.")
    if status in (401, 403):
        return "AI service authentication is temporarily unavailable. Check the Groq API key configuration."
    if status == 400:
        detail = _provider_message(response) if response is not None else ""
        if detail:
            return f"The AI service rejected the request: {detail}"
        return "The AI service rejected the request. Please try again."
    if status == 404:
        detail = _provider_message(response) if response is not None else ""
        return f"The configured AI model or endpoint is unavailable{': ' + detail if detail else '.'}"
    if status == 413:
        return "This conversation is too large for the AI service. Try starting a new chat or shortening the request."
    if status >= 500:
        return "The AI service is temporarily unavailable. Please try again shortly."
    detail = _provider_message(response) if response is not None else ""
    return f"The AI service could not complete that request{': ' + detail if detail else '.'}"


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
            raise GroqProviderError("The AI service timed out. Please try again.", code="groq_timeout") from exc
        except httpx.RequestError as exc:
            raise GroqProviderError("Unable to connect to the AI service. Please try again.", code="groq_connection_error") from exc
        last = response
        if response.status_code != 429:
            return response
        if attempt < settings.groq_retry_attempts:
            await asyncio.sleep(_retry_seconds(response, attempt))
    return last  # type: ignore[return-value]


async def call_groq_detailed(system_prompt: str, history: List[Dict], user_message: str) -> dict:
    if not settings.groq_token:
        raise GroqProviderError("The AI service is not configured yet.", code="groq_not_configured")
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
        error = _friendly_error(response.status_code, response)
        raise GroqProviderError(error, status_code=response.status_code, code="groq_http_error")
    try:
        data = response.json(); choice = data["choices"][0]
        answer = str(choice["message"]["content"] or "").strip(); usage = data.get("usage") or {}
        return {"answer": answer, "model": data.get("model", selected_model),
                "input_tokens": usage.get("prompt_tokens") or usage.get("input_tokens"),
                "output_tokens": usage.get("completion_tokens") or usage.get("output_tokens"),
                "finish_reason": choice.get("finish_reason"),
                "latency_ms": int((time.perf_counter() - started) * 1000)}
    except Exception as exc:
        raise GroqProviderError("The AI service returned an invalid response.", code="groq_invalid_response") from exc


async def stream_groq(system_prompt: str, history: List[Dict], user_message: str) -> AsyncIterator[dict]:
    """Yield normalized Groq stream events and preserve provider failure identity."""
    if not settings.groq_token:
        raise GroqProviderError("The AI service is not configured yet.", code="groq_not_configured")
    messages = _messages(system_prompt, history, user_message)
    models = [settings.groq_model]
    if settings.groq_enable_fallback and settings.groq_fallback_model and settings.groq_fallback_model != settings.groq_model:
        models.append(settings.groq_fallback_model)

    last_error: Exception | None = None
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
                        # Streaming responses are not read automatically. Read the
                        # body BEFORE inspecting it, otherwise httpx raises
                        # ResponseNotRead and the UI receives the misleading generic error.
                        await response.aread()
                        error = _friendly_error(response.status_code, response)
                        if isinstance(error, str):
                            last_error = GroqProviderError(error, status_code=response.status_code, code="groq_http_error")
                            if response.status_code == 429 and model_index < len(models) - 1:
                                continue
                            raise last_error
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
        except GroqRateLimitError as exc:
            last_error = exc
            if model_index < len(models) - 1:
                continue
            raise
        except asyncio.CancelledError:
            raise
        except (httpx.TimeoutException,) as exc:
            raise GroqProviderError("The AI service timed out. Please try again.", code="groq_timeout") from exc
        except httpx.RequestError as exc:
            raise GroqProviderError("Unable to connect to the AI service. Please try again.", code="groq_connection_error") from exc
    if last_error:
        raise last_error
    raise GroqProviderError("The AI service could not complete that request.", code="groq_provider_error")


async def call_groq(system_prompt: str, history: List[Dict], user_message: str) -> str:
    data = await call_groq_detailed(system_prompt, history, user_message)
    if not data["answer"]:
        raise GroqProviderError("The AI service returned an empty response.", code="groq_empty_response")
    return data["answer"]
