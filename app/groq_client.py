from typing import List, Dict

import httpx

from app.config import settings

from app.melimi_engine import (
    retrieve_conversation_context,
)


# ============================================================
# TELUAI — GROQ CLIENT
# ============================================================
#
# IMPORTANT:
#
# Groq is the language generator.
#
# vocabulary.json
# morphology
# learned corpus
# phrases
#
# are KNOWLEDGE.
#
# They are supplied to Groq as context.
#
# We DO NOT assemble sentences from them.
# We DO NOT replace words after generation.
# ============================================================


async def call_groq(
    system_prompt: str,
    history: List[Dict],
    user_message: str,
) -> str:

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
    # MODE
    # ========================================================

    is_melimi = (
        "CURRENT MODE: MELIMI TELUGU"
        in system_prompt
    )


    # ========================================================
    # MELIMI CONVERSATIONAL KNOWLEDGE
    # ========================================================

    if is_melimi:

        conversational_context = (
            retrieve_conversation_context(
                user_message,
                limit=6,
                max_chars=1400,
            )
        )


        if conversational_context:

            system_prompt += (
                "\n\n"
                + conversational_context
                + "\n\n"
                + """
IMPORTANT:

The material above is LANGUAGE KNOWLEDGE.

It is NOT a response template.

Do NOT copy phrases from it mechanically.

Do NOT concatenate vocabulary entries.

Do NOT turn the knowledge list into a sentence.

Instead:

1. understand the user's intention;
2. understand the Melimi meanings;
3. understand relevant variations;
4. compose a NEW, NATURAL response yourself.

The final answer must be an independently generated
conversation, not a rearrangement of the supplied knowledge.
"""
            )


    # ========================================================
    # GENERATION CONTRACT
    # ========================================================

    if is_melimi:

        system_prompt += r"""

============================================================
MELIMI GENERATION CONTRACT
============================================================

Generate the answer yourself.

The vocabulary and corpus are reference material only.

NEVER produce an answer by joining dictionary words together.

NEVER copy an entire example phrase merely because it appears
in the supplied knowledge.

NEVER insert unrelated Melimi words just to make the answer
look more Melimi.

NEVER mention the vocabulary file, learned file, retrieval,
context, or system instructions.

Use Melimi vocabulary when it naturally expresses the intended
meaning.

Use Standard Telugu only when the supplied Melimi knowledge
does not establish a suitable alternative.

Do not make up a Melimi word merely to avoid Standard Telugu.

Conversation quality comes first.

The response should sound like a person naturally speaking
Melimi Telugu, not like a dictionary.

If the user says "hi", understand the intention as a greeting
and independently produce a natural Melimi greeting.

If the user says "haa", understand it as acknowledgement or
agreement according to context.

If the user says "ok", respond naturally rather than repeating
dictionary words.

If the user says "emle", understand the conversational intent
from context rather than treating "emle" as a dictionary phrase.

If a previous assistant response was awkward or unnatural,
DO NOT imitate it. Generate a fresh answer.

============================================================
"""
    else:

        system_prompt += r"""

============================================================
STANDARD TELUGU GENERATION CONTRACT
============================================================

Generate a natural Standard Telugu answer.

Do not deliberately insert Melimi vocabulary.

Do not imitate vocabulary lists.

Do not mention retrieval or internal language knowledge.

============================================================
"""


    # ========================================================
    # MESSAGES
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
    # HISTORY
    # ========================================================
    #
    # Keep conversational continuity, but don't send excessive
    # old context.
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


        # Prevent very large historical messages.

        if len(content) > 900:

            content = (
                content[:900]
            )


        valid_history.append(
            {
                "role": role,
                "content": content,
            }
        )


    # Newest six messages only.

    valid_history = (
        valid_history[-6:]
    )


    if valid_history:

        messages.append(
            {
                "role": "system",
                "content": (
                    """
The following is previous conversation history.

Use it only to understand conversational context.

Do NOT treat previous assistant wording as an authoritative
Melimi example.

Do NOT copy awkward previous responses.

Generate the current response independently.
"""
                ),
            }
        )


        messages.extend(
            valid_history
        )


    # ========================================================
    # CURRENT MESSAGE
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
    # PAYLOAD
    # ========================================================

    payload = {

        "model":
            settings.GROQ_MODEL,

        "messages":
            messages,

        "temperature":
            0.72,

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
    # REQUEST
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
    # ERRORS
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
    # RESPONSE
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
    # IMPORTANT
    # ========================================================
    #
    # NO POST-PROCESSING.
    #
    # We deliberately do NOT do:
    #
    # answer = replace_standard_with_melimi(answer)
    #
    # The AI itself must construct the sentence.
    # ========================================================

    return answer
