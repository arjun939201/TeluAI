
import asyncio
import re
from typing import Dict, List, Optional

import httpx

from app.config import settings

# Caps how many Groq calls this process fires at once. Extra calls queue up
# on this semaphore instead of all hitting the API in the same instant and
# blowing the per-minute token budget together.
_CONCURRENCY_GATE = asyncio.Semaphore(max(1, settings.groq_max_concurrent_requests))


def _messages(system_prompt: str, history: List[Dict], user_message: str) -> List[Dict]:
    messages = [{"role": "system", "content": system_prompt}]
    per_turn_cap = settings.max_history_chars_per_turn
    for item in (history or [])[-settings.max_history_turns:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()[:per_turn_cap]})
    messages.append({"role": "user", "content": user_message.strip()})
    return messages


def _parse_wait_seconds(value: Optional[str]) -> Optional[float]:
    """Groq sends reset/retry-after headers like '46s', '1m3.5s', or a plain
    number of seconds. Parse whatever shape shows up; return None if we
    can't make sense of it."""
    if not value:
        return None
    value = value.strip()
    try:
        return float(value)
    except ValueError:
        pass
    match = re.match(r"^(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?$", value)
    if match and (match.group(1) or match.group(2)):
        minutes = float(match.group(1) or 0)
        seconds = float(match.group(2) or 0)
        return minutes * 60 + seconds
    return None


def _backoff_seconds(response: httpx.Response) -> float:
    """Figure out how long to wait before retrying a 429, preferring Groq's
    own headers over a guess, capped so one bad response can't stall the
    whole request for minutes."""
    h = response.headers
    candidates = [
        _parse_wait_seconds(h.get("retry-after")),
        _parse_wait_seconds(h.get("x-ratelimit-reset-tokens")),
        _parse_wait_seconds(h.get("x-ratelimit-reset-requests")),
    ]
    wait = next((c for c in candidates if c is not None), 2.0)
    return max(0.5, min(wait, settings.groq_max_backoff_seconds))


async def _post_to_groq(model: str, system_prompt: str, history: List[Dict], user_message: str) -> httpx.Response:
    payload = {
        "model": model,
        "messages": _messages(system_prompt, history, user_message),
        "temperature": settings.temperature,
        "top_p": 0.92,
        "max_tokens": settings.max_response_tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_token}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(connect=10, read=60, write=30, pool=10)

    async with _CONCURRENCY_GATE:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                return await client.post(settings.groq_url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise RuntimeError("Groq API request timed out.") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Unable to connect to Groq API: {exc}") from exc


def _extract_answer(response: httpx.Response) -> str:
    try:
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError("Groq returned an invalid response.") from exc

    answer = str(answer or "").strip()
    if not answer:
        raise RuntimeError("Groq returned an empty response.")
    return answer


def _raise_for_non_rate_limit_error(response: httpx.Response) -> None:
    if response.status_code in (401, 403):
        raise RuntimeError("Groq API authentication failed. Check GROQ_TOKEN.")
    try:
        detail = response.json()
    except Exception:
        detail = response.text
    raise RuntimeError(f"Groq API error {response.status_code}: {detail}")


async def _call_model_with_retry(model: str, system_prompt: str, history: List[Dict], user_message: str) -> str:
    """Call one model, retrying on 429s using Groq's own reset headers.
    Raises RuntimeError with the last rate-limit message if all attempts
    are exhausted."""
    attempts = max(1, settings.groq_retry_attempts + 1)
    last_rate_limit_message = None

    for attempt in range(attempts):
        response = await _post_to_groq(model, system_prompt, history, user_message)

        if response.status_code == 200:
            return _extract_answer(response)

        if response.status_code == 429:
            last_rate_limit_message = _rate_limit_message(response, model)
            if attempt < attempts - 1:
                await asyncio.sleep(_backoff_seconds(response))
                continue
            raise RuntimeError(last_rate_limit_message)

        _raise_for_non_rate_limit_error(response)

    # Unreachable, but keeps type-checkers happy.
    raise RuntimeError(last_rate_limit_message or "Groq API rate limit reached.")


async def call_groq(system_prompt: str, history: List[Dict], user_message: str) -> str:
    if not settings.groq_token:
        raise RuntimeError("GROQ_TOKEN is not set.")

    try:
        return await _call_model_with_retry(settings.groq_model, system_prompt, history, user_message)
    except RuntimeError as primary_error:
        is_rate_limit = "rate limit" in str(primary_error).lower()
        fallback_model = settings.groq_fallback_model
        can_fall_back = (
            settings.groq_enable_fallback
            and is_rate_limit
            and fallback_model
            and fallback_model != settings.groq_model
        )
        if not can_fall_back:
            raise

        try:
            return await _call_model_with_retry(fallback_model, system_prompt, history, user_message)
        except RuntimeError as fallback_error:
            # Surface the fallback's own error, but make clear both models
            # were tried so the real story doesn't get lost.
            raise RuntimeError(
                f"Primary model ({settings.groq_model}) is rate limited; "
                f"fallback model ({fallback_model}) also failed: {fallback_error}"
            ) from fallback_error


def _rate_limit_message(response: httpx.Response, model: str) -> str:
    """Surface Groq's own rate-limit headers so the real cause (RPM vs TPM vs
    daily) and wait time are visible instead of a generic 429 message."""
    h = response.headers
    retry_after = h.get("retry-after")
    remaining_requests = h.get("x-ratelimit-remaining-requests")
    remaining_tokens = h.get("x-ratelimit-remaining-tokens")
    reset_requests = h.get("x-ratelimit-reset-requests")
    reset_tokens = h.get("x-ratelimit-reset-tokens")

    parts = [f"Groq API rate limit reached for model {model}."]
    if remaining_requests is not None:
        parts.append(f"requests remaining: {remaining_requests} (resets in {reset_requests or '?'})")
    if remaining_tokens is not None:
        parts.append(f"tokens remaining: {remaining_tokens} (resets in {reset_tokens or '?'})")
    if retry_after:
        parts.append(f"retry after {retry_after}s")
    if not (remaining_requests or remaining_tokens or retry_after):
        parts.append(
            "This is usually the free-tier per-minute token budget, not the "
            "daily quota. Wait about a minute and try again, or shorten the "
            "conversation."
        )
    return " ".join(parts)
