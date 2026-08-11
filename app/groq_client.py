from typing import List, Dict

import httpx

from app.config import settings


async def call_groq(
    system_prompt: str,
    history: List[Dict],
    user_message: str,
) -> str:
    """
    Send a conversation to Groq.

    TeluAI's Melimi Telugu intelligence is controlled mainly by:
    - app/prompts.py
    - app/vocab.py
    - app/morphology.py
    - app/learner.py

    This file is only responsible for communicating with Groq.
    """

    # ---------------------------------------------------------
    # API KEY CHECK
    # ---------------------------------------------------------

    if not settings.GROQ_TOKEN:
        raise RuntimeError(
            "GROQ_TOKEN is not set. "
            "Add your Groq API key to the environment variables."
        )

    # ---------------------------------------------------------
    # BUILD MESSAGES
    # ---------------------------------------------------------

    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    # Keep only valid conversation messages.
    for item in history or []:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")

        if role not in {"user", "assistant"}:
            continue

        if not isinstance(content, str):
            continue

        content = content.strip()

        if not content:
            continue

        messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    # Current user message
    messages.append(
        {
            "role": "user",
            "content": user_message.strip(),
        }
    )

    # ---------------------------------------------------------
    # GROQ REQUEST
    # ---------------------------------------------------------

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": messages,

        # Slight creativity is useful for natural
        # Melimi Telugu conversation.
        "temperature": 0.7,

        # Enough room for a useful answer while
        # preventing unnecessarily huge responses.
        "max_tokens": 1024,

        # Keep generation from becoming repetitive.
        "top_p": 0.9,
    }

    headers = {
        "Authorization": f"Bearer {settings.GROQ_TOKEN}",
        "Content-Type": "application/json",
    }

    # ---------------------------------------------------------
    # CALL GROQ
    # ---------------------------------------------------------

    timeout = httpx.Timeout(
        connect=10.0,
        read=60.0,
        write=30.0,
        pool=10.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:

        response = await client.post(
            settings.GROQ_URL,
            json=payload,
            headers=headers,
        )

    # ---------------------------------------------------------
    # ERROR HANDLING
    # ---------------------------------------------------------

    if response.status_code != 200:

        try:
            error_data = response.json()
        except Exception:
            error_data = response.text

        raise RuntimeError(
            f"Groq API error {response.status_code}: {error_data}"
        )

    # ---------------------------------------------------------
    # PARSE RESPONSE
    # ---------------------------------------------------------

    try:
        data = response.json()

        choices = data.get("choices", [])

        if not choices:
            raise RuntimeError(
                "Groq returned no choices."
            )

        message = choices[0].get("message", {})

        answer = message.get("content", "")

        if not isinstance(answer, str):
            raise RuntimeError(
                "Groq returned an invalid response."
            )

        answer = answer.strip()

        if not answer:
            raise RuntimeError(
                "Groq returned an empty response."
            )

        return answer

    except RuntimeError:
        raise

    except Exception as exc:
        raise RuntimeError(
            f"Unable to parse Groq response: {exc}"
        ) from exc
