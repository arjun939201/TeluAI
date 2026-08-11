# Melimi Telugu Chatbot

A FastAPI backend that chats in either **Standard Telugu** or **Melimi Telugu**,
toggled per request. Uses Groq's free API (Llama models) for generation, and
your own vocabulary/grammar data to steer the style.

## How it works

1. You keep your Melimi Telugu vocabulary + example sentence pairs in
   `data/vocabulary.json` and `data/examples.json`.
2. On every chat request, `app/vocab.py` pulls the vocab entries whose
   standard-Telugu word appears in the user's message (simple keyword match,
   no paid embedding API needed).
3. `app/prompts.py` builds a system prompt: base persona + a handful of
   few-shot example pairs + the retrieved vocab, so the model learns the
   *style* (word choice, honorific register) rather than just swapping words.
4. `app/groq_client.py` calls Groq's free chat completions endpoint.
5. `app/main.py` exposes `POST /chat` which the toggle-enabled frontend in
   `static/index.html` calls.

## Local setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then paste your Groq key into .env
uvicorn app.main:app --reload
```

Open http://localhost:8000 to use the test chat UI, or POST to
`http://localhost:8000/chat` directly:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "ఏవైనా హాళికాను నిక్కువాలు చెప్పు", "mode": "melimi", "history": []}'
```

## Get a free Groq API key

1. Go to https://console.groq.com
2. Sign up with email or Google (no credit card)
3. Create an API key and put it in `.env` as `GROQ_API_KEY`

Free tier: ~14,400 requests/day, 30 requests/min on most models. Plenty for a
personal project. Default model is `llama-3.1-8b-instant` (fast, generous
limits) — change `GROQ_MODEL` in `.env` if you want a bigger model like
`llama-3.3-70b-versatile`.

## Deploy to Render (free)

1. Push this folder to a new GitHub repo
2. On https://render.com, "New +" → "Web Service" → connect the repo
3. Render will read `render.yaml` automatically, or set manually:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variable `GROQ_API_KEY` in the Render dashboard (Settings
   → Environment) — never commit your real key to GitHub
5. Deploy. Free tier spins down after inactivity, so the first request after
   idle takes ~30s to wake up.

## Folder structure

```
melimi-telugu-bot/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app + /chat endpoint
│   ├── config.py         # env var loading
│   ├── models.py         # request/response schemas
│   ├── groq_client.py    # Groq API wrapper
│   ├── vocab.py           # vocabulary loading + retrieval
│   └── prompts.py         # system prompt construction
├── data/
│   ├── vocabulary.json    # standard <-> melimi word pairs (edit/extend this)
│   └── examples.json      # full-sentence few-shot pairs (edit/extend this)
├── static/
│   └── index.html         # simple test UI with mode toggle
├── requirements.txt
├── .env.example
├── .gitignore
└── render.yaml
```

## Extending your data

- `data/vocabulary.json`: add entries as
  `{"standard": "సాయం", "melimi": "తోడ్పాటు", "note": "help/assistance"}`
- `data/examples.json`: add full conversational pairs as
  `{"standard": "...", "melimi": "..."}` — these matter more than the word
  list for teaching the model tone and grammar shifts, since Melimi Telugu
  isn't 1:1 word substitution.

Larger vocab/grammar files (thousands of entries) will slow down naive
keyword matching. If you get there, swap `vocab.py`'s `retrieve()` function
for a simple SQLite `LIKE` query or a local (free) embedding search — no
need to change anything else.
