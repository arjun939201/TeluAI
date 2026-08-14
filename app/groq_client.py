from typing import Dict, List, NamedTuple
import asyncio
import httpx
import re

from app.config import settings


class GroqCompletion(NamedTuple):
    text: str
    truncated: bool  # True only when the provider stopped due to the output
                      # token limit (finish_reason == "length"), never guessed
                      # from string length/content.


def _messages(system_prompt: str, history: List[Dict], user_message: str) -> List[Dict]:
    system_prompt = (system_prompt or "")[:settings.max_system_chars]
    user_message = (user_message or "")[:settings.max_user_chars]
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


def _duration_seconds(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    total = 0.0
    matched = False
    for num, unit in re.findall(r"([0-9]+(?:\.[0-9]+)?)(ms|h|m|s)", value):
        matched = True
        n = float(num)
        total += n / 1000 if unit == "ms" else n * {"s": 1, "m": 60, "h": 3600}[unit]
    if matched:
        return total
    try:
        return float(value)
    except ValueError:
        return None


def _rate_limit_wait(response: httpx.Response) -> float | None:
    h = response.headers
    return (
        _duration_seconds(h.get("retry-after"))
        or _duration_seconds(h.get("x-ratelimit-reset-tokens"))
        or _duration_seconds(h.get("x-ratelimit-reset-requests"))
    )


def _rate_limit_message(response: httpx.Response) -> str:
    wait = _rate_limit_wait(response)
    if wait is not None:
        wait_text = f"{max(1, round(wait))} seconds" if wait < 60 else f"{round(wait / 60, 1)} minutes"
        return f"Groq is temporarily rate-limited. Please try again in about {wait_text}."
    return "Groq is temporarily rate-limited. Please wait a short time and try again."


async def call_groq(system_prompt: str, history: List[Dict], user_message: str) -> GroqCompletion:
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

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(2):
            try:
                response = await client.post(settings.groq_url, json=payload, headers=headers)
            except httpx.TimeoutException as exc:
                raise RuntimeError("Groq API request timed out.") from exc
            except httpx.RequestError as exc:
                raise RuntimeError(f"Unable to connect to Groq API: {exc}") from exc

            if response.status_code == 200:
                try:
                    data = response.json()
                    choice = data["choices"][0]
                    answer = choice["message"]["content"]
                    finish_reason = choice.get("finish_reason")
                except Exception as exc:
                    raise RuntimeError("Groq returned an invalid response.") from exc
                answer = str(answer or "").strip()
                if not answer:
                    raise RuntimeError("Groq returned an empty response.")
                # Never silently drop the fact that a reply was cut short.
                # finish_reason == "length" means the provider stopped
                # because it hit max_tokens, not because the answer was
                # actually complete.
                return GroqCompletion(text=answer, truncated=(finish_reason == "length"))

            if response.status_code == 429:
                wait = _rate_limit_wait(response)
                # One bounded retry after a short provider-supplied reset. This
                # helps TPM/RPM windows without creating a retry storm.
                if attempt == 0 and wait is not None and 0 < wait <= 20:
                    await asyncio.sleep(wait + 0.25)
                    continue
                raise RuntimeError(_rate_limit_message(response))

            if response.status_code == 413:
                raise RuntimeError("Groq request is too large for the current TPM/model limit. The app has already reduced context; shorten the user message or lower the model/context limits.")
            if response.status_code in (401, 403):
                raise RuntimeError("Groq API authentication failed. Check GROQ_TOKEN.")
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise RuntimeError(f"Groq API error {response.status_code}: {detail}")

    raise RuntimeError("Groq request failed.")
