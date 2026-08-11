from typing import List, Dict

import httpx

from app.config import settings


# ============================================================
# TELUAI — GROQ CLIENT
# ============================================================

async def call_groq(
    system_prompt: str,
    history: List[Dict],
    user_message: str,
) -> str:
    """
    Send a compact Melimi Telugu conversation to Groq.

    TeluAI's language intelligence comes from:
    - app/prompts.py
    - app/vocab.py
    - app/morphology.py
    - app/learner.py

    This file handles only the Groq API communication.
    """


    # ========================================================
    # API KEY
    # ========================================================

    if not settings.GROQ_TOKEN:

        raise RuntimeError(
            "GROQ_TOKEN is not set. "
            "Add your Groq API key to Render environment variables."
        )


    # ========================================================
    # VALIDATE SYSTEM PROMPT
    # ========================================================

    if not isinstance(
        system_prompt,
        str,
    ):

        raise RuntimeError(
            "Invalid system prompt."
        )


    system_prompt = (
        system_prompt.strip()
    )


    if not system_prompt:

        raise RuntimeError(
            "System prompt is empty."
        )


    # ========================================================
    # BUILD MESSAGES
    # ========================================================

    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]


    # ========================================================
    # RECENT HISTORY ONLY
    # ========================================================
    #
    # main.py already limits history.
    # This is an additional safety layer.
    #
    # Keep the newest 8 messages.
    # ========================================================

    valid_history = []


    for item in (
        history or []
    ):

        if not isinstance(
            item,
            dict,
        ):

            continue


        role = item.get(
            "role"
        )

        content = item.get(
            "content"
        )


        if role not in {
            "user",
            "assistant",
        }:

            continue


        if not isinstance(
            content,
            str,
        ):

            continue


        content = (
            content.strip()
        )


        if not content:

            continue


        # Safety limit for old messages.
        #
        # The current user message is not subject to
        # this particular history limit.

        if len(content) > 900:

            content = (
                content[
                    :900
                ]
            )


        valid_history.append(
            {
                "role": role,
                "content": content,
            }
        )


    valid_history = (
        valid_history[-8:]
    )


    messages.extend(
        valid_history
    )


    # ========================================================
    # CURRENT USER MESSAGE
    # ========================================================

    current_message = (
        user_message
        or ""
    ).strip()


    if not current_message:

        raise RuntimeError(
            "User message is empty."
        )


    messages.append(
        {
            "role": "user",
            "content": current_message,
        }
    )


    # ========================================================
    # GROQ REQUEST
    # ========================================================
    #
    # 512 output tokens is enough for normal conversational
    # answers and substantially reduces output-side usage.
    #
    # The important Melimi knowledge is provided as INPUT
    # context by main.py/prompts.py.
    # ========================================================

    payload = {
        "model": settings.GROQ_MODEL,

        "messages": messages,

        "temperature": 0.6,

        "max_tokens": 512,

        "top_p": 0.9,
    }


    # ========================================================
    # HEADERS
    # ========================================================

    headers = {
        "Authorization": (
            f"Bearer {settings.GROQ_TOKEN}"
        ),
        "Content-Type": "application/json",
    }


    # ========================================================
    # TIMEOUT
    # ========================================================

    timeout = httpx.Timeout(
        connect=10.0,
        read=60.0,
        write=30.0,
        pool=10.0,
    )


    # ========================================================
    # CALL GROQ
    # ========================================================

    try:

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            response = await client.post(
                settings.GROQ_URL,
                json=payload,
                headers=headers,
            )

    except httpx.TimeoutException as exc:

        raise RuntimeError(
            "Groq API request timed out."
        ) from exc

    except httpx.RequestError as exc:

        raise RuntimeError(
            f"Unable to connect to Groq API: {exc}"
        ) from exc


    # ========================================================
    # ERROR HANDLING
    # ========================================================

    if response.status_code != 200:

        try:

            error_data = (
                response.json()
            )

        except Exception:

            error_data = (
                response.text
            )


        # ----------------------------------------------------
        # RATE LIMIT
        # ----------------------------------------------------

        if response.status_code == 429:

            raise RuntimeError(
                "Groq API rate limit reached. "
                "Your Groq organization has exhausted "
                "the current model/token allowance. "
                "Please wait for the quota window to refresh "
                "or use a model with available quota."
            )


        # ----------------------------------------------------
        # AUTHENTICATION
        # ----------------------------------------------------

        if response.status_code in {
            401,
            403,
        }:

            raise RuntimeError(
                "Groq API authentication failed. "
                "Check GROQ_TOKEN in Render environment variables."
            )


        # ----------------------------------------------------
        # OTHER API ERRORS
        # ----------------------------------------------------

        raise RuntimeError(
            f"Groq API error "
            f"{response.status_code}: "
            f"{error_data}"
        )


    # ========================================================
    # PARSE RESPONSE
    # ========================================================

    try:

        data = response.json()

    except Exception as exc:

        raise RuntimeError(
            "Groq returned invalid JSON."
        ) from exc


    choices = data.get(
        "choices",
        [],
    )


    if not choices:

        raise RuntimeError(
            "Groq returned no choices."
        )


    first_choice = choices[0]


    if not isinstance(
        first_choice,
        dict,
    ):

        raise RuntimeError(
            "Groq returned an invalid choice."
        )


    message = first_choice.get(
        "message",
        {},
    )


    if not isinstance(
        message,
        dict,
    ):

        raise RuntimeError(
            "Groq returned an invalid message."
        )


    answer = message.get(
        "content",
        "",
    )


    if not isinstance(
        answer,
        str,
    ):

        raise RuntimeError(
            "Groq returned an invalid response."
        )


    answer = (
        answer.strip()
    )


    if not answer:

        raise RuntimeError(
            "Groq returned an empty response."
        )


    return answer
