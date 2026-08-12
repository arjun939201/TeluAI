
from typing import Dict, List
import httpx

from app.config import settings


def _messages(system_prompt: str, history: List[Dict], user_message: str) -> List[Dict]:
    messages = [{"role": "system", "content": system_prompt}]
    for item in (history or [])[-settings.max_history_turns:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()[:1800]})
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
        "max_tokens": 600,
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
            raise RuntimeError("Groq API rate limit reached. Please wait for the quota window to refresh.")
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
