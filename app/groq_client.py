from typing import Dict, List
import time
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


def _human_reset(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    # Groq may return strings such as "1m2.4s". Preserve that as the wait
    # duration instead of showing a confusing raw reset timestamp.
    return value


def _rate_limit_message(response: httpx.Response) -> str:
    h = response.headers
    retry_after = _human_reset(h.get("retry-after"))
    reset = _human_reset(h.get("x-ratelimit-reset-tokens")) or _human_reset(h.get("x-ratelimit-reset-requests"))
    if retry_after:
        return f"Groq is temporarily rate-limited. Please try again in about {retry_after}."
    if reset:
        return f"Groq is temporarily rate-limited. Please try again in about {reset}."
    return "Groq is temporarily rate-limited. Please try again shortly."


async def call_groq_detailed(system_prompt: str, history: List[Dict], user_message: str) -> dict:
    if not settings.groq_token:
        raise RuntimeError("GROQ_TOKEN is not set.")
    messages = _messages(system_prompt, history, user_message)
    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": settings.temperature,
        "top_p": 0.92,
        "max_tokens": settings.max_response_tokens,
    }
    headers = {"Authorization": f"Bearer {settings.groq_token}", "Content-Type": "application/json"}
    timeout = httpx.Timeout(connect=10, read=90, write=30, pool=10)
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(settings.groq_url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise RuntimeError("Groq API request timed out. Please try again.") from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Unable to connect to Groq API. Please try again.") from exc

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
            "model": data.get("model", settings.groq_model),
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
