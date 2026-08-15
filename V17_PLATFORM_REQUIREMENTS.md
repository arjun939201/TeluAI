# TeluAI v17 — Melimi AI Platform

This release combines the existing Melimi language engine with the persistent application platform.

## Core language architecture

- Melimi Telugu is treated as a distinct language/register system.
- Standard/Mixed Telugu surface forms are analyzed grammatically first.
- Supported inflectional/derivational material is reduced to a root.
- The Standard/Mixed root is looked up in the Melimi root dictionary.
- The Melimi root is substituted and the same grammatical operation is reapplied.
- Root dictionaries store roots; they do not store every plural/case/derived variant.
- Melimi noun and verb derivational systems remain generic and category-sensitive.
- Non-`ం` Melimi lexical forms can be noun/adjective-capable where authoritative corpus evidence supports them.
- Unsupported morphology is not invented.
- Output is locally validated/repaired after generation.

## AI architecture

- Authoritative Melimi corpus/rules are separate from Groq generation.
- Retrieval sends only relevant language evidence to Groq.
- Deterministic known operations and local answers avoid Groq calls.
- Conversation context is compacted to reduce TPM/request-size pressure.
- Provider rate-limit errors are converted into user-facing wait-duration messages.
- Long answers support continuation instead of silently restarting.

## Persistent platform

PostgreSQL is the production database when `DATABASE_URL` is configured. Local development falls back to SQLite.

Stored dynamic data includes:

- users
- sessions
- conversations
- messages
- user settings
- learning candidates
- feedback
- usage

Chat-time language teaching is stored as `PENDING` learning candidates and is not automatically promoted to authoritative Melimi knowledge.

## Authentication

Unauthenticated users see Login/Register before entering the chat. Passwords are PBKDF2-SHA256 hashed and sessions are stored as hashed random tokens.

## Render

Configure `DATABASE_URL` with the Render PostgreSQL connection string and `GROQ_TOKEN` as a secret environment variable. No credentials are committed to Git.
