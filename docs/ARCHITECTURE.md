# TeluAI Architecture

## Canonical project structure

TeluAI uses the following ownership rules for source code:

- `app/` contains backend application code.
- `app/melimi/` is the canonical runtime home for Melimi language logic.
- `app/conversation/` is the canonical home for conversation state, understanding, and planning.
- `app/learning/` is the canonical home for learning/review workflows.
- `app/memory/` is the canonical home for persistent-memory behavior.
- `app/retrieval/` is the canonical home for retrieval helpers.
- `static/` is the single canonical frontend tree.
- `tests/` is the canonical test tree.
- `migrations/` is the canonical database migration tree.
- `docs/` contains project documentation and historical design notes.

## Runtime flow

```text
HTTP request
    ↓
FastAPI API layer
    ↓
Conversation state + intent
    ↓
Authoritative Language Space retrieval
    ↓
Groq generation
    ↓
Melimi policy / validation
    ↓
Deterministic repair when explicitly supported
    ↓
Response
```

## Important boundaries

### Language authority

Language data is authoritative only when it has passed the project's review/MASTER workflow. Missing vocabulary is not permission to invent a Melimi word.

### Melimi runtime

Melimi-specific grammar, morphology, lexical rules, registry, validation, firewall, indexing, and language-engine behavior belong under `app/melimi/`. New Melimi runtime modules should not be added as unrelated top-level `app/*.py` modules.

### Frontend

`static/` is the only frontend source tree. Backend startup serves this directory directly. Do not create another `app/static/` frontend tree.

### Database

Database persistence is being consolidated around `app/db/` and the existing application services. New database code should not create another parallel database abstraction.

## Refactoring rule

Prefer consolidating an existing capability over adding a second implementation. Before creating a new module, search the repository for an existing implementation of the same responsibility.

This architecture document describes the target ownership model; cleanup is intentionally incremental so behavior and the Melimi corpus are not changed during structural refactoring.
