
from typing import Dict, List
import httpx

from app.config import settings


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


async def call_groq(system_prompt: str, history: List[Dict], user_message: str) -> str:
    if not settings.groq_token:
        raise RuntimeError("GROQ_TOKEN is not set.")

    payload = {
        "model": settings.groq_model,
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

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(settings.groq_url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise RuntimeError("Groq API request timed out.") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Unable to connect to Groq API: {exc}") from exc

    if response.status_code != 200:
        if response.status_code == 429:
            raise RuntimeError(_rate_limit_message(response))
        if response.status_code in (401, 403):
            raise RuntimeError("Groq API authentication failed. Check GROQ_TOKEN.")
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Groq API error {response.status_code}: {detail}")

    try:
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError("Groq returned an invalid response.") from exc

    answer = str(answer or "").strip()
    if not answer:
        raise RuntimeError("Groq returned an empty response.")
    return answer


def _rate_limit_message(response: httpx.Response) -> str:
    """Surface Groq's own rate-limit headers so the real cause (RPM vs TPM vs
    daily) and wait time are visible instead of a generic 429 message."""
    h = response.headers
    retry_after = h.get("retry-after")
    remaining_requests = h.get("x-ratelimit-remaining-requests")
    remaining_tokens = h.get("x-ratelimit-remaining-tokens")
    reset_requests = h.get("x-ratelimit-reset-requests")
    reset_tokens = h.get("x-ratelimit-reset-tokens")

    parts = ["Groq API rate limit reached."]
    if remaining_requests is not None:
        parts.append(f"requests remaining: {remaining_requests} (resets in {reset_requests or '?'})")
    if remaining_tokens is not None:
        parts.append(f"tokens remaining: {remaining_tokens} (resets in {reset_tokens or '?'})")
    if retry_after:
        parts.append(f"retry after {retry_after}s")
    if not (remaining_requests or remaining_tokens or retry_after):
        parts.append(
            "This is usually the free-tier per-minute token budget (as low as "
            "6,000-12,000 TPM on llama-3.3-70b-versatile), not the daily quota. "
            "Wait about a minute and try again, or shorten the conversation."
        )
    return " ".join(parts)
