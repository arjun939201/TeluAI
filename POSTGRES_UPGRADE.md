# PostgreSQL upgrade (2026-08-15)

This implements the local-first architecture: a Postgres layer sits in front
of Groq so known language operations, repeated questions, and per-user
context are handled without spending Groq's free-tier token budget, and
Melimi Telugu can grow through a controlled, human-approved chat learning
loop instead of Groq inventing/self-teaching vocabulary.

## What's new

| File | Purpose |
|---|---|
| `app/db/models.py` | SQLAlchemy tables: `learning_candidates`, `approved_knowledge`, `query_cache`, `user_memory` |
| `app/db/engine.py` | Async Postgres engine/session bootstrap. Fully optional — degrades to no-op if `DATABASE_URL` is unset or unreachable |
| `app/db/repository.py` | All DB reads/writes. Every function checks availability first and never raises into the chat pipeline |
| `app/local_answer.py` | **Tier 0** — answers simple `"X అంటే ఏమిటి?"` questions from DB-approved or local `vocabulary.json`/corpus knowledge, zero Groq calls |
| `app/teaching.py` | Detects chat-time teaching statements (`"X = Y"`, `"X ని Y అంటారు"`) and proposes them as pending learning candidates |
| `app/knowledge_version.py` | Cheap fingerprint of the local knowledge base, used to invalidate the cache automatically when knowledge changes |
| `static/admin.html` | Token-gated dashboard at `/admin` to approve/reject pending candidates |

`app/main.py` and `app/config.py` were updated to wire all of this into `/chat`. No existing file's *behavior* changes if `DATABASE_URL` is unset — it's additive.

## The pipeline, per `/chat` request

```
User message
     │
     ▼
Tier 0 — deterministic (app/local_answer.py)
  Known "X అంటే ఏమిటి?" + no history + Melimi mode?
  → check approved_knowledge (Postgres), then vocabulary.json / corpus
  → answer directly. Groq usage: 0.
     │ (no match)
     ▼
Tier 1 — cache (app/db/repository.py: get_cached_answer)
  Fresh conversation (no history)? Have we answered this exact
  question before, under the current knowledge_version?
  → serve the cached answer. Groq usage: 0.
     │ (no match)
     ▼
Tier 2 — Groq (unchanged app/prompts.py + app/groq_client.py)
  Full prompt built as before, sent to Groq.
  → answer cached for next time (if eligible).
     │
     ▼
Chat-time learning capture (app/teaching.py)
  If the message was a teaching statement ("X = Y"), it's queued
  as a *pending* learning_candidates row — never applied automatically.
     │
     ▼
ChatResponse.source tells you which tier answered: "deterministic" | "cache" | "groq"
```

## Approval workflow (the "don't let Groq self-teach" principle)

1. A user teaches a word in chat → `learning_candidates` row, `status="pending"`.
2. You open `/admin` (or call `GET /admin/learning/pending`), review it.
3. Approve → it's copied into `approved_knowledge`, and Tier 0 can answer
   it from then on. Reject → it's marked rejected and ignored.
4. Nothing is ever written into `approved_knowledge` without this step.
   Groq's own output is never auto-saved as Melimi vocabulary.

The existing manual `/melimi/register` endpoint (writes straight into the
Git-tracked corpus file, optionally auto-committing to GitHub) is untouched
— it's still there for the "I've verified this myself" flow. The new
Postgres flow is for the lighter-weight "someone mentioned a word in
passing chat" case, which now doesn't get lost or bypass review.

## Per-user memory

If the client sends a stable `user_id` on `ChatRequest` (e.g. a UUID kept in
`localStorage`), TeluAI persists a small set of explicit facts (name, stated
likes/dislikes — reusing the existing conservative extractor in
`app/memory/manager.py`) in `user_memory`, and recalls them on future
requests/sessions, not just from client-sent history. Omitting `user_id`
disables this entirely — it's opt-in per client.

## New environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | *(unset)* | Postgres connection string. Render gives you this in `postgres://...` form; it's auto-converted to the asyncpg driver. **Everything below is inert until this is set.** |
| `ADMIN_TOKEN` | *(unset)* | Required header value (`X-Admin-Token`) for `/admin/learning/*`. Endpoints return 503 until this is set. |
| `ENABLE_LOCAL_FIRST` | `true` | Tier 0 deterministic answers |
| `ENABLE_RESPONSE_CACHE` | `true` | Tier 1 answer cache |
| `ENABLE_CHAT_LEARNING_CAPTURE` | `true` | Auto-detect teaching statements in chat |

## Setting this up on Render

1. Render dashboard → **New** → **PostgreSQL**. Free tier is fine to start.
2. Copy the **Internal Database URL** it gives you.
3. On your TeluAI web service → Environment → add `DATABASE_URL` = that
   value, and `ADMIN_TOKEN` = any long random string you choose.
4. Redeploy. On startup, TeluAI connects and creates the four tables
   automatically (`Base.metadata.create_all` — no manual migration step).
5. Visit `https://<your-app>/admin`, paste your `ADMIN_TOKEN`, and you'll
   see the (initially empty) review dashboard.
6. Check `GET /db/health` any time to confirm `"available": true`.

If you ever need to reset, dropping and recreating the Postgres instance is
safe — TeluAI recreates the schema on the next startup.

## What this does and doesn't fix

It **does**: cut Groq usage for repeated/known-answer questions toward
zero, shrink what gets sent to Groq for anything it *is* still needed for
being unaffected by this change (already handled locally via the existing
`app/melimi/index.py` retrieval), and give Melimi Telugu a real, auditable
growth path.

It **doesn't**: increase Groq's actual rate limit — that's still whatever
your Groq plan allows (see `CHANGES_RATE_LIMIT_FIX.md` for the retry/backoff/
fallback-model resilience layer already in place for when Tier 2 is still
needed and does hit a 429).
