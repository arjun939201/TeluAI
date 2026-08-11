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

    try:

        vocab_matches = retrieve_vocab(
            message,
            limit=18,
        )

    except TypeError:

        # Compatibility with an older retrieve_vocab()
        # signature.
        vocab_matches = retrieve_vocab(
            message
        )

    except Exception:

        vocab_matches = []


    # ========================================================
    # COMPLETE VOCABULARY CONTEXT
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


    # --------------------------------------------------------
    # Fallback if retrieve_context() did not provide text.
    # --------------------------------------------------------

    if not vocabulary_context:

        vocabulary_context = (
            _format_vocabulary(
                vocab_matches
            )
        )


    # ========================================================
    # MORPHOLOGICAL UNDERSTANDING
    # ========================================================
    #
    # This helps understand surface variations such as:
    #
    #     ఎడాటం
    #     ఎడాటాలు
    #     ఎడాటాన్ని
    #     ఎడాటానికి
    #
    # when they can be connected to a known vocabulary base.
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


    # ========================================================
    # ADD MORPHOLOGY TO AI CONTEXT
    # ========================================================

    morphology_text = (
        _format_morphology(
            morphology_context
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
    # learner.py stores information learned from Melimi
    # texts:
    #
    # - words
    # - phrases
    # - sentences
    # - observed variations
    #
    # That information is now passed to the AI.
    # ========================================================

    learned_context = ""

    if req.mode == "melimi":

        try:

            learned_context = (
                build_learned_context(
                    message,
                    limit=10,
                    max_chars=6000,
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
    # CONVERSATION HISTORY
    # ========================================================

    history = []

    for turn in (
        req.history or []
    ):

        try:

            history.append(
                turn.model_dump()
            )

        except AttributeError:

            if isinstance(
                turn,
                dict,
            ):

                history.append(
                    turn
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
    # CLEAN RESPONSE
    # ========================================================

    reply = str(
        reply or ""
    ).strip()

    if not reply:

        raise HTTPException(
            status_code=502,
            detail="AI returned an empty response.",
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
    # MORPHOLOGY SURFACES
    # ========================================================

    root_candidates = (
        _get_morphology_surfaces(
            morphology_context
        )
    )


    # ========================================================
    # RESPONSE
    # ========================================================

    return ChatResponse(

        reply=reply,

        mode=req.mode,

        matched_vocab=(
            matched_vocab
        ),

        # Your current models expect these fields.
        # Grammar-specific retrieval is not currently
        # implemented in vocab.py, so leave them empty
        # instead of importing nonexistent functions.
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
    max_chars=7000,
):

    if not entries:

        return ""


    lines = [
        "RELEVANT AUTHORITATIVE MELIMI VOCABULARY:"
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
                f" | meaning: {meaning}"
            )


        if note:

            line += (
                f" | note: {note}"
            )


        lines.append(
            line
        )


    result = "\n".join(
        lines
    )


    if len(result) > max_chars:

        result = result[
            :max_chars
        ]


    return result


# ============================================================
# MORPHOLOGY FORMATTER
# ============================================================

def _format_morphology(
    morphology_context,
    max_chars=5000,
):

    if not morphology_context:

        return ""


    lines = [
        "MELIMI MORPHOLOGICAL UNDERSTANDING:"
    ]


    for item in (
        morphology_context
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


        lines.append(
            f"- Surface form: {surface}"
        )


        for entry in (
            matches or []
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


            if not melimi:

                continue


            line = (
                f"  → known Melimi base: "
                f"{melimi}"
            )


            if standard:

                line += (
                    f" | standard: "
                    f"{standard}"
                )


            lines.append(
                line
            )


    result = "\n".join(
        lines
    )


    if len(result) > max_chars:

        result = result[
            :max_chars
        ]


    return result


# ============================================================
# MORPHOLOGY SURFACE LIST
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
# LEARN MELIMI TEXT
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
