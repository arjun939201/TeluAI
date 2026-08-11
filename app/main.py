import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models import ChatRequest, ChatResponse
from app.vocab import retrieve_vocab, get_examples
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

    system_prompt = build_system_prompt(req.mode, vocab_matches, examples)
    history = [turn.model_dump() for turn in req.history]

    try:
        reply = await call_groq(system_prompt, history, req.message)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ChatResponse(
        reply=reply,
        mode=req.mode,
        matched_vocab=[v["standard"] for v in vocab_matches],
    )
