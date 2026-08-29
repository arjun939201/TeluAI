# TeluAI

**Telugu-first AI conversation and Melimi Telugu language intelligence platform.**

TeluAI combines FastAPI, PostgreSQL-backed language knowledge, contextual Telugu understanding, deterministic Melimi morphology, a curated Language Space, authentication, learning/review workflows, conversation history, user-controlled memory, admin operations, and Groq generation.

## Architecture

```text
Browser
  ↓
FastAPI / canonical ASGI composition (app.server:app)
  ├─ authentication / authorization
  ├─ workspace boundaries
  ├─ canonical chat transport (JSON + SSE)
  ├─ conversation application
  ├─ Melimi language engine
  ├─ learning / Language Space
  └─ LLM provider boundary
          ↓
      Groq adapter
          ↓
 PostgreSQL language + account data
```

The main application is intentionally not a generic chatbot. Language authority is versioned and provenance-aware; unknown Melimi vocabulary is not silently invented.

## Runtime entrypoint

`app.server:app` is the canonical production ASGI composition. It explicitly assembles the runtime boundaries that the base FastAPI module defines.

Use it for local production-style runs:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.server:app --reload
```

Docker and Render use the same `app.server:app` entrypoint.

## Configuration

Copy `.env.example` and configure the required values.

Important variables include:

```text
GROQ_API_KEY                  # GROQ_TOKEN remains supported for compatibility
GROQ_MODEL
GROQ_FALLBACK_MODEL
DATABASE_URL
OWNER_EMAILS
TELUAI_OWNER_EMAIL
SESSION_DAYS
COOKIE_SECURE
CORS_ORIGINS
TRUST_PROXY_HEADERS
SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD / SMTP_FROM
GITHUB_TOKEN / GITHUB_REPO / GITHUB_BRANCH / GITHUB_LANGUAGE_FILE
```

Never expose provider or GitHub tokens to the browser.

## Product behavior

- Conversation context is bounded and state-aware.
- Standard Telugu is an explicit mode; the native conversation path uses Melimi language intelligence.
- Language contributions from regular users enter review before becoming authoritative.
- Published language records are `MASTER` and create a new knowledge version.
- User memory is explicit and user-controlled.
- Chat streaming uses the backend's native SSE transport.
- Provider failures expose useful, non-secret error information.

## Security baseline

TeluAI includes HttpOnly/SameSite session cookies, server-side role authorization, authentication/upload/chat rate limits, security headers, restricted CORS when configured, bounded uploads and ZIP extraction, audit logging, and production API docs disabled by default.

## Testing

CI performs:

1. dependency installation and `pip check`
2. Python compilation
3. frontend JavaScript syntax checking
4. repository hygiene checks
5. the complete pytest suite
6. offline language evaluation

Run locally:

```bash
pytest -q --import-mode=importlib
```

## Deployment

Recommended Render deployment:

```text
Render Web Service
        │
        ├── DATABASE_URL → Render PostgreSQL
        ├── GROQ_API_KEY
        └── optional SMTP / GitHub configuration
```

Start command:

```text
uvicorn app.server:app --host 0.0.0.0 --port $PORT
```

Health endpoints:

```text
GET /health
GET /health/ready
```

`/health/ready` verifies database connectivity and is suitable for readiness checks.

## Language authority

The runtime authority flow is:

```text
PENDING / PROPOSED
        ↓ review
MASTER
        ↓ versioned runtime retrieval
Melimi engine
```

The historical full Melimi corpus is not fabricated into this repository. Restore authoritative corpus material through the Language Space/content workflow when available.

## Engineering principles

- Elementary excellence.
- One canonical runtime path per responsibility.
- Root causes before new components.
- No fake loading, results, integrations, or AI functionality.
- Preserve working vertical slices while refactoring.
- No microservices, Kubernetes, Redis, or vector database without measured need.
