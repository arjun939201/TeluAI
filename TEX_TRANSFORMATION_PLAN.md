# TEX — Melimi Telugu AI Transformation Plan

## Product objective

TeluAI is a normal-conversation Telugu AI bot that learns explicitly taught Melimi/native Telugu vocabulary and grammar from chat, stores validated user-specific knowledge in PostgreSQL, and reuses that knowledge in future conversations.

## Engineering principles

- Preserve the canonical `app.server:app` production boundary.
- Keep normal conversation as the primary product experience.
- Do not convert ordinary conversation into learning automatically.
- Treat explicit user teaching as a learning signal requiring validation.
- Keep learned knowledge scoped to the correct user.
- Keep authoritative language knowledge distinct from LLM guesses.
- Prefer deterministic/local language processing where established.
- Persist learning atomically with provenance and audit information.
- Never expose provider credentials to the browser.
- Verify every meaningful change with tests/build checks.

## Transformation workstreams

### P0 — Runtime and persistence reliability
- verify canonical chat path end-to-end
- verify Render startup and readiness
- verify PostgreSQL persistence and migrations
- remove or isolate duplicate/legacy runtime paths after repository-wide usage verification

### P1 — Conversation learning loop
- identify explicit Melimi teaching in natural chat
- normalize and validate candidate vocabulary/grammar
- prevent ordinary conversation and model guesses from becoming knowledge
- persist validated personal learning records
- retrieve relevant learned knowledge for subsequent chats
- protect against concurrent/stale knowledge updates

### P1 — Language quality
- Telugu/Roman Telugu/mixed-input routing
- native-first response behavior
- Melimi vocabulary and grammar handling
- unsupported-form preservation
- deterministic transformation firewall
- authority/provenance separation

### P1 — Data integrity and provenance
- explicit transaction boundary for language mutation
- provenance for learned knowledge
- knowledge versioning
- audit events
- request/prompt/evidence metadata where safe

### P2 — Security
- authentication/authorization audit
- prompt-injection resistance for retrieved/user-supplied language content
- input validation
- secret handling
- rate limiting and abuse controls
- safe error handling

### P2 — Evaluation and testing
- expand behavioral tests
- adversarial language tests
- persistence tests
- concurrent update tests
- migration/schema checks
- provider-independent offline evaluation
- provider-backed evaluation only when explicitly available

### P2/P3 — Product quality
- focused chat UX
- responsive/mobile behavior
- accessibility
- loading/error/empty states
- reliable history
- clear learning feedback without turning the product into a lab interface

## Definition of done

The primary user can converse naturally with TeluAI in Telugu; explicitly taught Melimi/native Telugu words and grammar are validated, safely persisted to Render PostgreSQL under the correct user, retrieved when relevant in later conversations, and protected from accidental or hallucinated learning. The application builds, starts, passes relevant tests, handles failures truthfully, and remains consistent with the architecture constitution.

## Current known architecture work

The repository's current world-class status identifies legacy chat orchestration cleanup, migration/runtime separation, possible duplicate database subsystem retirement, stronger language-mutation transaction boundaries, structured provenance, adversarial security tests, deeper CI/schema validation, and provider-backed AI evaluation as remaining principal work.

TEX will address these incrementally and only where repository evidence confirms they are required.
