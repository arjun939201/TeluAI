from typing import List, Dict

import httpx

from app.config import settings

from app.melimi_engine import (
    retrieve_conversation_context,
    validate_melimi_response,
)


# ============================================================
# TELUAI — GROQ CLIENT
# ============================================================


async def call_groq(
    system_prompt: str,
    history: List[Dict],
    user_message: str,
) -> str:
    """
    Send the conversation to Groq.

    Melimi-specific retrieval and final validation happen
    locally so they do NOT require another Groq request.
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
    # SYSTEM PROMPT
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
    # DETECT MODE
    # ========================================================
    #
    # main.py already passes mode into prompts.py.
    #
    # prompts.py produces:
    #
    # CURRENT MODE: MELIMI TELUGU
    #
    # or:
    #
    # CURRENT MODE: STANDARD TELUGU
    #
    # ========================================================

    is_melimi = (
        "CURRENT MODE: MELIMI TELUGU"
        in system_prompt
    )


    # ========================================================
    # ADD CONVERSATIONAL MELIMI CONTEXT
    # ========================================================
    #
    # This is especially important for:
    #
    # hi
    # hello
    # thanks
    # help
    #
    # where normal vocabulary retrieval may have little
    # Telugu material to match.
    #
    # ========================================================

    if is_melimi:

        conversation_context = (
            retrieve_conversation_context(
                user_message,
                limit=6,
                max_chars=1400,
            )
        )


        if conversation_context:

            system_prompt += (
                "\n\n"
                + conversation_context
                + "\n\n"
                + """
Use the relevant Melimi conversational vocabulary above.
Do not ignore it merely because the user's message is short
or written in English.
"""
            )


    # ========================================================
    # BUILD MESSAGES
    # ========================================================

    messages: List[
        Dict[str, str]
    ] = [

        {
            "role": "system",
            "content": system_prompt,
        }

    ]


    # ========================================================
    # RECENT HISTORY
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

    payload = {

        "model":
            settings.GROQ_MODEL,

        "messages":
            messages,

        "temperature":
            0.6,

        "max_tokens":
            512,

        "top_p":
            0.9,

    }


    # ========================================================
    # HEADERS
    # ========================================================

    headers = {

        "Authorization":
            f"Bearer {settings.GROQ_TOKEN}",

        "Content-Type":
            "application/json",

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


        if response.status_code == 429:

            raise RuntimeError(
                "Groq API rate limit reached. "
                "Your Groq organization has exhausted "
                "the current model/token allowance. "
                "Please wait for the quota window to refresh."
            )


        if response.status_code in {
            401,
            403,
        }:

            raise RuntimeError(
                "Groq API authentication failed. "
                "Check GROQ_TOKEN in Render environment variables."
            )


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


    # ========================================================
    # FINAL MELIMI VALIDATION
    # ========================================================
    #
    # Only Melimi mode is validated.
    #
    # Standard mode is NEVER rewritten.
    #
    # Example:
    #
    #   సహాయం
    #
    # becomes:
    #
    #   బాసట
    #
    # because vocabulary.json says:
    #
    #   standard = సహాయం
    #   melimi   = బాసట
    #
    # No hardcoded mapping exists in this file.
    # ========================================================

    if is_melimi:

        answer, _changes = (
            validate_melimi_response(
                answer
            )
        )


    return answer
