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

    # --------------------------------------------------------
    # VOCABULARY
    # --------------------------------------------------------

    vocab_matches = retrieve_vocab(
        req.message
    )


    # --------------------------------------------------------
    # MORPHOLOGICAL UNDERSTANDING
    # --------------------------------------------------------

    morphology_context = []

    if req.mode == "melimi":

        morphology_context = analyze_text(
            req.message,
            VOCABULARY,
        )


    # --------------------------------------------------------
    # MELIMI RESOURCES
    # --------------------------------------------------------

    examples = []

    phrases = []

    grammar_matches = {
        "suffixes": [],
        "prefixes": [],
        "reduplication": [],
    }


    root_candidates = []


    if req.mode == "melimi":

        examples = get_examples()

        phrases = get_phrases()

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
        mode=req.mode,
        vocab_matches=vocab_matches,
        examples=examples,
        grammar_matches=grammar_matches,
        phrases=phrases,
        morphology_context=morphology_context,
    )


    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    history = [
        turn.model_dump()
        for turn in req.history
    ]


    # --------------------------------------------------------
    # GENERATE
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
    # RESPONSE CHECK
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
