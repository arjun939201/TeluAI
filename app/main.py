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
    LearnVocabRequest,
    LearnGrammarRequest,
    LearnPhraseRequest,
    LearnResponse,
)

from app.vocab import (
    retrieve_vocab,
    retrieve_grammar,
    find_root_candidates,
    get_examples,
    get_phrases,
    add_vocab_entry,
    add_grammar_rule,
    add_phrase,
    find_standard_melimi_alternatives,
    VOCABULARY,
)

from app.morphology import (
    analyze_text,
)

from app.prompts import (
    build_system_prompt,
    build_melimi_correction_prompt,
)

from app.groq_client import call_groq


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

STATIC_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            __file__
        )
    ),
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
    # AUTHORITATIVE VOCABULARY
    # ========================================================

    vocab_matches = retrieve_vocab(
        message
    )


    # ========================================================
    # MORPHOLOGICAL UNDERSTANDING
    # ========================================================

    morphology_context = []

    if req.mode == "melimi":

        morphology_context = analyze_text(
            message,
            VOCABULARY,
        )


    # ========================================================
    # MELIMI RESOURCES
    # ========================================================

    examples = []

    phrases = []

    grammar_matches = {
        "suffixes": [],
        "prefixes": [],
        "reduplication": [],
    }

    root_candidates = []


    if req.mode == "melimi":

        # ----------------------------------------------------
        # Vocabulary examples
        # ----------------------------------------------------

        examples = get_examples(
            message
        )


        # ----------------------------------------------------
        # Known phrases
        # ----------------------------------------------------

        phrases = get_phrases()


        # ----------------------------------------------------
        # Grammar
        # ----------------------------------------------------

        grammar_matches = (
            retrieve_grammar(
                message
            )
        )


        # ----------------------------------------------------
        # Possible roots
        # ----------------------------------------------------

        root_candidates = (
            find_root_candidates(
                message
            )
        )


    # ========================================================
    # LEARNED CORPUS
    # ========================================================
    #
    # This is the important new connection.
    #
    # Texts previously learned by learner.py can now influence
    # the current AI response.
    #
    # Example:
    #
    # User text:
    #
    #     హాళికాను ఎడాటం
    #
    # Later user:
    #
    #     హాళికాను ఎడాటాన్ని
    #
    # The learned phrase / variation evidence can be supplied
    # to Groq along with the authoritative vocabulary.
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

            # Learned corpus must never make the entire
            # chatbot unavailable.
            learned_context = ""


    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    system_prompt = build_system_prompt(

        vocabulary_context=(
            _build_vocabulary_context(
                vocab_matches,
                examples,
                phrases,
                grammar_matches,
                morphology_context,
                root_candidates,
            )
        ),

        learned_context=(
            learned_context
        ),
    )


    # ========================================================
    # HISTORY
    # ========================================================

    history = [
        turn.model_dump()
        for turn in req.history
    ]


    # ========================================================
    # GENERATE
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
    # MELIMI RESPONSE CHECK
    # ========================================================

    if (
        req.mode == "melimi"
        and reply
    ):

        alternatives = (
            find_standard_melimi_alternatives(
                reply
            )
        )


        if alternatives:

            correction_prompt = (
                build_melimi_correction_prompt(
                    reply,
                    alternatives,
                )
            )


            try:

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

                # The first response is still usable
                # if the correction request fails.
                pass


    # ========================================================
    # RESPONSE
    # ========================================================

    return ChatResponse(

        reply=reply,

        mode=req.mode,

        matched_vocab=[
            v.get(
                "standard",
                "",
            )
            for v in vocab_matches
        ],

        matched_grammar_suffixes=[
            r.get(
                "suffix",
                "",
            )
            for r in grammar_matches.get(
                "suffixes",
                [],
            )
        ],

        matched_grammar_prefixes=[
            r.get(
                "element",
                "",
            )
            for r in grammar_matches.get(
                "prefixes",
                [],
            )
        ],

        root_candidates=(
            root_candidates
        ),
    )


# ============================================================
# BUILD VOCABULARY CONTEXT
# ============================================================

def _build_vocabulary_context(
    vocab_matches,
    examples,
    phrases,
    grammar_matches,
    morphology_context,
    root_candidates,
):

    sections = []


    # ========================================================
    # AUTHORITATIVE VOCABULARY
    # ========================================================

    if vocab_matches:

        lines = [
            "AUTHORITATIVE MELIMI VOCABULARY:"
        ]

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

        sections.append(
            "\n".join(lines)
        )


    # ========================================================
    # VOCABULARY EXAMPLES
    # ========================================================

    if examples:

        sections.append(
            "RELEVANT MELIMI EXAMPLES:\n"
            + str(examples)
        )


    # ========================================================
    # PHRASES
    # ========================================================

    if phrases:

        sections.append(
            "RELEVANT MELIMI PHRASES:\n"
            + str(phrases)
        )


    # ========================================================
    # GRAMMAR
    # ========================================================

    grammar_lines = []


    for key in (
        "suffixes",
        "prefixes",
        "reduplication",
    ):

        values = grammar_matches.get(
            key,
            [],
        )

        if not values:
            continue

        grammar_lines.append(
            f"{key.upper()}:"
        )

        for item in values:

            grammar_lines.append(
                "- "
                + str(item)
            )


    if grammar_lines:

        sections.append(
            "MELIMI GRAMMAR:\n"
            + "\n".join(
                grammar_lines
            )
        )


    # ========================================================
    # MORPHOLOGY
    # ========================================================

    if morphology_context:

        sections.append(
            "MORPHOLOGICAL UNDERSTANDING:\n"
            + str(
                morphology_context
            )
        )


    # ========================================================
    # ROOT CANDIDATES
    # ========================================================

    if root_candidates:

        sections.append(
            "POSSIBLE MELIMI ROOTS:\n"
            + str(
                root_candidates
            )
        )


    # ========================================================
    # FINAL CONTEXT
    # ========================================================

    context = "\n\n".join(
        sections
    )

    # Prevent the vocabulary portion from becoming
    # unnecessarily enormous.
    if len(context) > 9000:

        context = context[
            :9000
        ]

    return context


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


# ============================================================
# LEARN VOCAB
# ============================================================

@app.post(
    "/learn/vocab",
    response_model=LearnResponse,
)
def learn_vocab(
    req: LearnVocabRequest,
):

    added = add_vocab_entry(
        req.standard,
        req.melimi,
        req.note,
    )

    return LearnResponse(
        added=added,
        message=(
            "Added to vocabulary.json"
            if added
            else
            "Already exists in vocabulary.json"
        ),
    )


# ============================================================
# LEARN GRAMMAR
# ============================================================

@app.post(
    "/learn/grammar",
    response_model=LearnResponse,
)
def learn_grammar(
    req: LearnGrammarRequest,
):

    added = add_grammar_rule(
        req.kind,
        req.element,
        req.meaning,
        req.examples,
        req.note,
    )

    return LearnResponse(
        added=added,
        message=(
            "Added to grammar.json"
            if added
            else
            "Already exists in grammar.json"
        ),
    )


# ============================================================
# LEARN PHRASE
# ============================================================

@app.post(
    "/learn/phrase",
    response_model=LearnResponse,
)
def learn_phrase(
    req: LearnPhraseRequest,
):

    added = add_phrase(
        req.standard,
        req.melimi,
    )

    return LearnResponse(
        added=added,
        message=(
            "Added to phrases.json"
            if added
            else
            "Already exists in phrases.json"
        ),
    )
