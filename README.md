# TeluAI

**Telugu-first AI conversation and Melimi Telugu language intelligence platform.**

TeluAI combines a conversational FastAPI application with PostgreSQL-backed
language knowledge, contextual Telugu understanding, Melimi morphology, a
curated Language Space, authentication, learning/approval workflows, history,
memory, admin operations, and Groq generation.

The product goal is not dictionary substitution. The core pipeline is:

```text
User message
    ↓
Normalization + Roman-Telugu hints
    ↓
Conversation state + intent
    ↓
Response planning
    ↓
Relevant authoritative language evidence
    ↓
Groq generation
    ↓
Melimi policy / bounded lexical audit
    ↓
Natural response
```

## Product principles

- **Conversation before analysis.** Short inputs such as `enti`, `haa`, `sare`,
  and `cheppu` are interpreted using the current conversation.
- **Language Space is authoritative.** MASTER entries outrank generic model
  knowledge.
- **No blind replacement.** Melimi output preserves grammatical function,
  meaning, tense, case, number, agreement, and context.
- **Root-first morphology.** Supported inflections/derivations are reduced to
  an authoritative root and the same grammatical operation is reapplied.
- **No invented authority.** Unknown or unsupported Melimi vocabulary is not
  silently invented merely to avoid a Standard Telugu word.
- **Uploaded/user language data is untrusted until reviewed.** Regular-user
  contributions enter the learning queue; admin/owner uploads may become
  MASTER data.

## Architecture

### Backend

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy 2.x
- PostgreSQL with psycopg
- Uvicorn
- Groq-compatible OpenAI-style chat API

Important application areas:

```text
app/
├── main.py                  API, lifecycle, chat orchestration
├── auth.py                  session authentication + authorization
├── database.py              PostgreSQL/SQLAlchemy persistence
├── learning/                unified contribution/review workflow
├── memory/                  memory extraction + explicit memory storage
├── conversation/            state, intent, planning
├── linguistics/             normalization and Telugu linguistic hints
├── melimi/                  grammar, roots, registry, firewall, index
├── language_space.py        unified curated language knowledge view
├── retrieval/               generic retrieval helpers
├── prompts.py               language/system output contracts
├── groq_client.py           resilient LLM client
├── github_sync.py           optional GitHub language synchronization
└── security.py              request limits + security headers
```

### Frontend

The UI is a static, mobile-first application under `static/`:

- `index.html` — main chat shell
- `js/professional.js` — chat, auth, history, settings, account interactions
- `admin.html` — admin shell
- `admin-*.html` — operational admin views
- `css/` — shared visual system

The frontend is intentionally separate from the language engine.

## Authentication and roles

Supported account roles:

- `guest`
- `user`
- `admin`
- `owner`

Authorization is enforced server-side through FastAPI dependencies. Client-side
role visibility is only a UX convenience and is never trusted for permissions.

Sessions use HttpOnly cookies with configurable Secure/SameSite behavior.
Passwords are stored as salted PBKDF2-SHA256 hashes. Password reset codes are
short-lived and reset operations revoke existing sessions.

## Conversation and memory

Conversation history is persisted per user. The chat pipeline uses bounded
recent history rather than blindly sending an unlimited transcript.

Persistent memory is user-controlled and is separate from temporary conversation
context. TeluAI does not silently convert arbitrary model output into permanent
personal memory.

## Melimi Telugu Language Space

The PostgreSQL language layer supports:

- dictionary roots
- grammar
- derivational rules
- affixes
- examples
- posts/content
- facts and notes
- uploaded language documents
- version records
- learning candidates
- audit history

The admin Language Space exposes these records through a unified interface with
search, filtering by type, version/status information, and provenance/source
information.

### Authority levels

```text
PENDING / PROPOSED
        ↓ review
MASTER
        ↓ runtime retrieval
Melimi language engine
```

A missing lexical entry is treated as missing evidence, not as permission to
invent a word.

## Learning workflow

Regular-user language contributions follow:

```text
Contribution
   ↓
Validation / size limits
   ↓
Learning Candidate
   ↓
Admin review
   ├── reject
   └── approve
          ↓
     authoritative language data
          ↓
       index refresh
```

Explicit `/word` and `/content` commands retain their syntax. Admin/owner
commands may write authoritative language data directly; regular-user commands
are queued for review to protect the language authority from poisoning.

## Upload security

Supported language packages:

- TXT
- Markdown
- JSON
- ZIP containing supported files

Upload limits include:

- 10 MB request limit
- 5 MB per ZIP member
- 10 MB total uncompressed ZIP content
- 50 ZIP members
- supported extensions only

Regular users cannot directly promote an upload to MASTER.

## AI reliability

The Groq client includes:

- bounded conversation/history sizes
- request timeouts
- retry handling for rate limiting
- Retry-After support
- exponential backoff
- optional model fallback
- bounded concurrent requests
- safe, non-secret error messages

The application also caches only context-independent new-chat responses. User
memory disables cross-request response caching to prevent personalization leaks.

## Security baseline

TeluAI includes:

- HttpOnly session cookies
- configurable Secure cookies
- SameSite protection
- server-side role authorization
- request rate limiting for authentication, chat, and uploads
- security response headers
- restricted CORS when explicitly configured
- disabled API docs by default in production
- bounded uploads and ZIP extraction
- audit logging for important account/language/admin actions
- no secrets committed to the repository

The old unpinned third-party ChatGPT GitHub Action was removed from this release
because it used a moving `main` reference and did not match its documented
inputs. GitHub repository synchronization remains a separate server-side
capability using `GITHUB_TOKEN`.

## Configuration

Copy `.env.example` and configure the required production values.

Important variables:

```text
GROQ_TOKEN
GROQ_MODEL
DATABASE_URL
OWNER_EMAILS
SESSION_DAYS
COOKIE_SECURE
CORS_ORIGINS
TRUST_PROXY_HEADERS
SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD / SMTP_FROM
GITHUB_TOKEN / GITHUB_REPO / GITHUB_BRANCH / GITHUB_LANGUAGE_FILE
```

For same-origin Render deployment, leave `CORS_ORIGINS` empty.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

The application can run its database migration/bootstrap sequence during
startup. For production, point `DATABASE_URL` at the Render PostgreSQL service.

## Testing

The CI pipeline performs:

1. dependency installation
2. `pip check`
3. Python compilation
4. frontend JavaScript syntax checking
5. repository hygiene checks
6. the full pytest suite

Run locally:

```bash
pytest -q --import-mode=importlib
```

## Production deployment

Recommended Render layout:

```text
Render Web Service
        │
        ├── DATABASE_URL ──→ Render PostgreSQL
        ├── GROQ_TOKEN
        ├── SMTP_* (optional password reset)
        └── OWNER_EMAILS
```

Start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health endpoints:

```text
GET /health
GET /health/ready
```

`/health/ready` verifies database connectivity and is appropriate for readiness
checks.

## Corpus status

The current repository does **not** contain the historical full Melimi corpus.
It contains `data/CORPUS_NOTE.txt`, which documents that the authoritative
language material was moved out of the repository and must be restored/imported
through the Language Space/content workflow.

TeluAI deliberately does not fabricate a replacement corpus. If you have the
original authoritative corpus, import it through an admin/owner-approved
Language Space package before treating those entries as production language
knowledge.

## GitHub language synchronization

GitHub synchronization is optional and server-side. The application can read
and write the configured language file through the GitHub Contents API when
`GITHUB_TOKEN` is configured with the required repository Contents permission.

Never expose the GitHub token to the browser or commit it to the repository.

## Design roadmap

The architecture is intended to grow toward:

1. full Telugu morphological parsing
2. richer dependency/clause analysis
3. semantic retrieval and ranking
4. language-entry confidence/provenance scoring
5. stronger learning conflict detection
6. shared/distributed rate limiting for multi-instance deployments
7. migration tooling with a formal migration history
8. automated Melimi naturalness evaluation
9. richer message actions and Markdown/code rendering
10. production observability/metrics and alerting

The goal remains the same: **excellent AI-powered Telugu and Melimi Telugu
language intelligence**, not a generic AI wrapper.
