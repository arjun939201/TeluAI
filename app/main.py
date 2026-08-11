import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.learner import (
    learn_text,
    build_learned_context,
)

from app.models import (
    ChatRequest,
    ChatResponse,
)

from app.vocab import (
    retrieve_vocab,
    retrieve_context,
    VOCABULARY,
)

from app.morphology import (
    analyze_text,
)

from app.prompts import (
    build_system_prompt,
)

from app.groq_client import (
    call_groq,
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="TeluAI - Melimi Telugu AI"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

STATIC_DIR = os.path.join(
    BASE_DIR,
    "static",
)


# ============================================================
# STATIC FILES
# ============================================================

if os.path.isdir(STATIC_DIR):

    app.mount(
        "/static",
        StaticFiles(
            directory=STATIC_DIR
        ),
        name="static",
    )


# ============================================================
# HOME
# ============================================================

@app.get("/")
def serve_index():

    index_file = os.path.join(
        STATIC_DIR,
        "index.html",
    )

    if not os.path.exists(index_file):

        raise HTTPException(
            status_code=404,
            detail="index.html not found.",
        )

    return FileResponse(
        index_file
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "TeluAI",
        "language": "Melimi Telugu",
    }


# ============================================================
# CHAT
# ============================================================

@app.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    req: ChatRequest,
):

    message = (
        req.message
        or ""
    ).strip()

    if not message:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )


    # ========================================================
    # AUTHORITATIVE VOCABULARY
    # ========================================================
    #
    # IMPORTANT:
    # Never send the whole vocabulary.json to Groq.
    #
    # Only retrieve a small number of relevant entries.
    # ========================================================

    try:

        vocab_matches = retrieve_vocab(
            message,
            limit=5,
        )

    except TypeError:

        try:

            vocab_matches = retrieve_vocab(
                message
            )

        except Exception:

            vocab_matches = []

    except Exception:

        vocab_matches = []


    # ========================================================
    # VOCABULARY CONTEXT
    # ========================================================

    vocabulary_context = ""

    try:

        context = retrieve_context(
            message
        )

        if isinstance(
            context,
            dict,
        ):

            vocabulary_context = str(
                context.get(
                    "text",
                    "",
                )
            )

        elif context:

            vocabulary_context = str(
                context
            )

    except Exception:

        vocabulary_context = ""


    # ========================================================
    # HARD LIMIT VOCABULARY CONTEXT
    # ========================================================
    #
    # Even if retrieve_context() returns a large amount of
    # text, do not send all of it to Groq.
    # ========================================================

    MAX_VOCAB_CHARS = 2200

    if len(
        vocabulary_context
    ) > MAX_VOCAB_CHARS:

        vocabulary_context = (
            vocabulary_context[
                :MAX_VOCAB_CHARS
            ]
        )


    # ========================================================
    # FALLBACK VOCABULARY
    # ========================================================

    if not vocabulary_context:

        vocabulary_context = (
            _format_vocabulary(
                vocab_matches,
                max_chars=2200,
            )
        )


    # ========================================================
    # MORPHOLOGY
    # ========================================================
    #
    # Analyze only the user's current message.
    #
    # Do NOT send the entire morphology database.
    # ========================================================

    morphology_context = []

    if req.mode == "melimi":

        try:

            morphology_context = analyze_text(
                message,
                VOCABULARY,
            )

        except Exception:

            morphology_context = []


    morphology_text = (
        _format_morphology(
            morphology_context,
            max_chars=1800,
        )
    )


    if morphology_text:

        if vocabulary_context:

            vocabulary_context += (
                "\n\n"
                + morphology_text
            )

        else:

            vocabulary_context = (
                morphology_text
            )


    # ========================================================
    # LEARNED CORPUS
    # ========================================================
    #
    # Only retrieve a SMALL relevant portion.
    #
    # The corpus itself can contain thousands of words.
    # That does NOT mean thousands of words should be sent
    # to Groq on every request.
    # ========================================================

    learned_context = ""

    if req.mode == "melimi":

        try:

            learned_context = (
                build_learned_context(
                    message,
                    limit=4,
                    max_chars=1800,
                )
            )

        except TypeError:

            try:

                learned_context = (
                    build_learned_context(
                        message
                    )
                )

            except Exception:

                learned_context = ""

        except Exception:

            learned_context = ""


    # ========================================================
    # FINAL LEARNED-CONTEXT LIMIT
    # ========================================================

    MAX_LEARNED_CHARS = 1800

    if len(
        learned_context
    ) > MAX_LEARNED_CHARS:

        learned_context = (
            learned_context[
                :MAX_LEARNED_CHARS
            ]
        )


    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    system_prompt = build_system_prompt(
        vocabulary_context=(
            vocabulary_context
        ),
        learned_context=(
            learned_context
        ),
    )


    # ========================================================
    # LIMIT SYSTEM PROMPT
    # ========================================================
    #
    # The actual Melimi rules remain in prompts.py.
    # This prevents accidental runaway context from the
    # retrieved material.
    #
    # We do NOT truncate the system prompt itself here because
    # doing so could cut an instruction in the middle.
    # ========================================================


    # ========================================================
    # CONVERSATION HISTORY
    # ========================================================
    #
    # Only send the most recent 4 turns.
    #
    # Old conversations are expensive and usually unnecessary
    # for understanding the current question.
    # ========================================================

    history = []

    raw_history = (
        req.history or []
    )

    # Keep only the newest 8 messages
    # = roughly 4 user/assistant exchanges.

    raw_history = raw_history[
        -8:
    ]


    for turn in raw_history:

        try:

            item = turn.model_dump()

        except AttributeError:

            if isinstance(
                turn,
                dict,
            ):

                item = turn

            else:

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


        # Prevent a very long old message from consuming
        # the entire context window.

        if len(content) > 900:

            content = (
                content[
                    :900
                ]
            )


        history.append(
            {
                "role": role,
                "content": content,
            }
        )


    # ========================================================
    # GROQ
    # ========================================================

    try:

        reply = await call_groq(
            system_prompt,
            history,
            message,
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "AI request failed: "
                + str(exc)
            ),
        )


    # ========================================================
    # RESPONSE
    # ========================================================

    reply = str(
        reply or ""
    ).strip()


    if not reply:

        raise HTTPException(
            status_code=502,
            detail=(
                "AI returned an empty response."
            ),
        )


    # ========================================================
    # MATCHED VOCABULARY
    # ========================================================

    matched_vocab = []


    for entry in (
        vocab_matches or []
    ):

        if not isinstance(
            entry,
            dict,
        ):

            continue


        standard = str(
            entry.get(
                "standard",
                "",
            )
        ).strip()


        melimi = str(
            entry.get(
                "melimi",
                "",
            )
        ).strip()


        if standard:

            matched_vocab.append(
                standard
            )

        elif melimi:

            matched_vocab.append(
                melimi
            )


    # ========================================================
    # MORPHOLOGICAL SURFACES
    # ========================================================

    root_candidates = (
        _get_morphology_surfaces(
            morphology_context
        )
    )


    # ========================================================
    # RETURN
    # ========================================================

    return ChatResponse(

        reply=reply,

        mode=req.mode,

        matched_vocab=(
            matched_vocab
        ),

        matched_grammar_suffixes=[],

        matched_grammar_prefixes=[],

        root_candidates=(
            root_candidates
        ),
    )


# ============================================================
# VOCABULARY FORMATTER
# ============================================================

def _format_vocabulary(
    entries,
    max_chars=2200,
):

    if not entries:

        return ""


    lines = [
        "RELEVANT MELIMI VOCABULARY:"
    ]


    for entry in entries:

        if not isinstance(
            entry,
            dict,
        ):

            continue


        standard = str(
            entry.get(
                "standard",
                "",
            )
        ).strip()


        melimi = str(
            entry.get(
                "melimi",
                "",
            )
        ).strip()


        note = str(
            entry.get(
                "note",
                "",
            )
        ).strip()


        meaning = str(
            entry.get(
                "meaning",
                entry.get(
                    "definition",
                    entry.get(
                        "english",
                        "",
                    ),
                ),
            )
        ).strip()


        if not (
            standard
            or melimi
        ):

            continue


        line = (
            f"- {standard}"
            f" → {melimi}"
        )


        if meaning:

            line += (
                f" | meaning: "
                f"{meaning}"
            )


        if note:

            line += (
                f" | note: "
                f"{note}"
            )


        lines.append(
            line
        )


        current = "\n".join(
            lines
        )


        if len(
            current
        ) >= max_chars:

            break


    result = "\n".join(
        lines
    )


    return result[
        :max_chars
    ]


# ============================================================
# MORPHOLOGY FORMATTER
# ============================================================

def _format_morphology(
    morphology_context,
    max_chars=1800,
):

    if not morphology_context:

        return ""


    lines = [
        "RELEVANT MELIMI WORD VARIATIONS:"
    ]


    for item in (
        morphology_context or []
    ):

        if not isinstance(
            item,
            dict,
        ):

            continue


        surface = str(
            item.get(
                "surface",
                "",
            )
        ).strip()


        matches = item.get(
            "matches",
            [],
        )


        if not surface:

            continue


        line = (
            f"- {surface}"
        )


        bases = []


        for entry in (
            matches or []
        ):

            if not isinstance(
                entry,
                dict,
            ):

                continue


            melimi = str(
                entry.get(
                    "melimi",
                    "",
                )
            ).strip()


            if melimi:

                bases.append(
                    melimi
                )


        if bases:

            line += (
                " → "
                + ", ".join(
                    bases[:3]
                )
            )


        lines.append(
            line
        )


        current = "\n".join(
            lines
        )


        if len(
            current
        ) >= max_chars:

            break


    return "\n".join(
        lines
    )[
        :max_chars
    ]


# ============================================================
# MORPHOLOGY SURFACES
# ============================================================

def _get_morphology_surfaces(
    morphology_context,
):

    result = []


    for item in (
        morphology_context or []
    ):

        if not isinstance(
            item,
            dict,
        ):

            continue


        surface = str(
            item.get(
                "surface",
                "",
            )
        ).strip()


        if surface:

            result.append(
                surface
            )


    return result


# ============================================================
# LEARN TEXT
# ============================================================

@app.post(
    "/learn/text",
)
def learn_melimi_text(
    text: str,
    document_id: str = "user_text",
):

    text = (
        text or ""
    ).strip()


    if not text:

        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty.",
        )


    try:

        result = learn_text(
            text=text,
            document_id=document_id,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )
