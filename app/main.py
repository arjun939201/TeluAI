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
    find_standard_terms,
    VOCABULARY,
)

from app.morphology import (
    analyze_text,
)

from app.prompts import (
    build_system_prompt,
    build_melimi_correction_prompt,
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
# STATIC
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

    return FileResponse(
        os.path.join(
            STATIC_DIR,
            "index.html",
        )
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

    message = req.message.strip()

    if not message:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )


    # ========================================================
    # 1. AUTHORITATIVE VOCABULARY
    # ========================================================

    vocab_matches = retrieve_vocab(
        message,
        limit=18,
    )


    # ========================================================
    # 2. COMPLETE VOCABULARY / PHRASE CONTEXT
    # ========================================================

    try:

        vocab_context = retrieve_context(
            message
        )

    except Exception:

        vocab_context = {
            "entries": vocab_matches,
            "text": "",
        }


    # ========================================================
    # 3. MORPHOLOGICAL UNDERSTANDING
    # ========================================================
    #
    # This connects surface forms to known Melimi words.
    #
    # Example:
    #
    # ఎడాటాలు
    # ఎడాటాన్ని
    # ఎడాటానికి
    #
    # can be analyzed against known vocabulary.
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
    # 4. LEARNED CORPUS
    # ========================================================
    #
    # learner.py stores:
    #
    # - words
    # - phrases
    # - sentences
    # - documents
    # - observed variations
    #
    # The learned information is now sent to Groq.
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

        except Exception:

            learned_context = ""


    # ========================================================
    # 5. BUILD AI CONTEXT
    # ========================================================

    vocabulary_text = ""

    if isinstance(
        vocab_context,
        dict,
    ):

        vocabulary_text = str(
            vocab_context.get(
                "text",
                "",
            )
        )

    elif vocab_context:

        vocabulary_text = str(
            vocab_context
        )


    # If retrieve_context returned nothing,
    # fall back to the direct vocabulary matches.

    if not vocabulary_text:

        vocabulary_text = (
            _format_vocabulary(
                vocab_matches
            )
        )


    morphology_text = (
        _format_morphology(
            morphology_context
        )
    )


    combined_vocabulary_context = (
        _combine_context(
            vocabulary_text,
            morphology_text,
        )
    )


    # ========================================================
    # 6. SYSTEM PROMPT
    # ========================================================

    system_prompt = build_system_prompt(

        vocabulary_context=(
            combined_vocabulary_context
        ),

        learned_context=(
            learned_context
        ),
    )


    # ========================================================
    # 7. CONVERSATION HISTORY
    # ========================================================

    history = [
        turn.model_dump()
        for turn in req.history
    ]


    # ========================================================
    # 8. ASK GROQ
    # ========================================================

    try:

        reply = await call_groq(
            system_prompt,
            history,
            message,
        )

    except RuntimeError as e:

        raise HTTPException(
            status_code=502,
            detail=str(e),
        )


    # ========================================================
    # 9. MELIMI RESPONSE VALIDATION
    # ========================================================
    #
    # Detect standard words in the generated answer
    # for which an established Melimi alternative exists.
    #
    # This does NOT blindly replace words.
    # A second Groq pass decides whether correction
    # is appropriate in context.
    # ========================================================

    if (
        req.mode == "melimi"
        and reply
    ):

        try:

            alternatives = (
                find_standard_terms(
                    reply
                )
            )

        except Exception:

            alternatives = []


        if alternatives:

            try:

                correction_prompt = (
                    build_melimi_correction_prompt(
                        reply,
                        alternatives,
                    )
                )

                corrected = await call_groq(
                    correction_prompt,
                    [],
                    reply,
                )

                if (
                    corrected
                    and corrected.strip()
                ):

                    reply = (
                        corrected.strip()
                    )

            except RuntimeError:

                # Keep the original answer if
                # the correction request fails.
                pass


    # ========================================================
    # 10. DEBUG INFORMATION
    # ========================================================

    matched_vocab = []

    for entry in vocab_matches:

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
    # 11. RETURN
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
            _get_morphology_surfaces(
                morphology_context
            )
        ),
    )


# ============================================================
# FORMAT VOCABULARY
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
# FORMAT MORPHOLOGY
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


    for item in morphology_context:

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


        for entry in matches:

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


            if melimi:

                lines.append(
                    f"  → known Melimi base: "
                    f"{melimi}"
                    + (
                        f" | standard: {standard}"
                        if standard
                        else ""
                    )
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
# COMBINE CONTEXT
# ============================================================

def _combine_context(
    vocabulary_text,
    morphology_text,
):

    sections = []


    if vocabulary_text:

        sections.append(
            vocabulary_text
        )


    if morphology_text:

        sections.append(
            morphology_text
        )


    return "\n\n".join(
        sections
    )


# ============================================================
# MORPHOLOGY SURFACES
# ============================================================

def _get_morphology_surfaces(
    morphology_context,
):

    result = []


    if not morphology_context:

        return result


    for item in morphology_context:

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

    if not text.strip():

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

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
