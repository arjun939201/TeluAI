import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
# STATIC FILES
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
        "status": "ok"
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

    # --------------------------------------------------------
    # VOCABULARY
    # --------------------------------------------------------

    vocab_matches = (
        retrieve_vocab(
            req.message
        )
    )


    # --------------------------------------------------------
    # MELIMI RESOURCES
    # --------------------------------------------------------

    examples = (
        get_examples()
        if req.mode == "melimi"
        else []
    )


    phrases = (
        get_phrases()
        if req.mode == "melimi"
        else []
    )


    grammar_matches = {
        "suffixes": [],
        "prefixes": [],
        "reduplication": [],
    }


    root_candidates = []


    if req.mode == "melimi":

        grammar_matches = (
            retrieve_grammar(
                req.message
            )
        )

        root_candidates = (
            find_root_candidates(
                req.message
            )
        )


    # --------------------------------------------------------
    # SYSTEM PROMPT
    # --------------------------------------------------------

    system_prompt = build_system_prompt(
        req.mode,
        vocab_matches,
        examples,
        grammar_matches,
        phrases,
    )


    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    history = [
        turn.model_dump()
        for turn in req.history
    ]


    # --------------------------------------------------------
    # FIRST GENERATION
    # --------------------------------------------------------

    try:

        reply = await call_groq(
            system_prompt,
            history,
            req.message,
        )

    except RuntimeError as e:

        raise HTTPException(
            status_code=502,
            detail=str(e),
        )


    # --------------------------------------------------------
    # MELIMI RESPONSE CHECK
    # --------------------------------------------------------

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

                corrected_reply = (
                    await call_groq(
                        correction_prompt,
                        [],
                        reply,
                    )
                )


                if (
                    corrected_reply
                    and corrected_reply.strip()
                ):

                    reply = (
                        corrected_reply.strip()
                    )


            except RuntimeError:

                # If the second Groq call fails,
                # keep the already-generated answer.
                pass


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

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
# LEARN VOCABULARY
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


    if added:

        message = (
            "Added to vocabulary.json"
        )

    else:

        message = (
            "Already exists in vocabulary.json"
        )


    return LearnResponse(
        added=added,
        message=message,
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


    if added:

        message = (
            f"Added to grammar.json "
            f"({req.kind})"
        )

    else:

        message = (
            f"Already exists in grammar.json "
            f"({req.kind})"
        )


    return LearnResponse(
        added=added,
        message=message,
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


    if added:

        message = (
            "Added to phrases.json"
        )

    else:

        message = (
            "Already exists in phrases.json"
        )


    return LearnResponse(
        added=added,
        message=message,
    )
