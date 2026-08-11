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
)
from app.prompts import build_system_prompt
from app.groq_client import call_groq

app = FastAPI(title="Melimi Telugu Chatbot")

# Allow calls from any frontend for now - tighten this to your real domain
# once you deploy a frontend somewhere other than this same server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    vocab_matches = retrieve_vocab(req.message)
    examples = get_examples() if req.mode == "melimi" else []
    phrases = get_phrases() if req.mode == "melimi" else []

    grammar_matches = {"suffixes": [], "prefixes": [], "reduplication": []}
    root_candidates: list = []
    if req.mode == "melimi":
        grammar_matches = retrieve_grammar(req.message)
        root_candidates = find_root_candidates(req.message)

    system_prompt = build_system_prompt(req.mode, vocab_matches, examples, grammar_matches, phrases)
    history = [turn.model_dump() for turn in req.history]

    try:
        reply = await call_groq(system_prompt, history, req.message)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ChatResponse(
        reply=reply,
        mode=req.mode,
        matched_vocab=[v["standard"] for v in vocab_matches],
        matched_grammar_suffixes=[r.get("suffix", "") for r in grammar_matches.get("suffixes", [])],
        matched_grammar_prefixes=[r.get("element", "") for r in grammar_matches.get("prefixes", [])],
        root_candidates=root_candidates,
    )


# ---------------------------------------------------------------------------
# Learning endpoints - call these once the user has CONFIRMED a piece of
# Melimi content (a word pair, a grammar rule, or a full phrase) is correct,
# so it gets persisted into data/vocabulary.json, data/grammar.json, or
# data/phrases.json respectively for all future conversations.
# ---------------------------------------------------------------------------

@app.post("/learn/vocab", response_model=LearnResponse)
def learn_vocab(req: LearnVocabRequest):
    added = add_vocab_entry(req.standard, req.melimi, req.note)
    msg = "Added to vocabulary.json" if added else "Already exists in vocabulary.json"
    return LearnResponse(added=added, message=msg)


@app.post("/learn/grammar", response_model=LearnResponse)
def learn_grammar(req: LearnGrammarRequest):
    added = add_grammar_rule(req.kind, req.element, req.meaning, req.examples, req.note)
    msg = f"Added to grammar.json ({req.kind})" if added else f"Already exists in grammar.json ({req.kind})"
    return LearnResponse(added=added, message=msg)


@app.post("/learn/phrase", response_model=LearnResponse)
def learn_phrase(req: LearnPhraseRequest):
    added = add_phrase(req.standard, req.melimi)
    msg = "Added to phrases.json" if added else "Already exists in phrases.json"
    return LearnResponse(added=added, message=msg)
