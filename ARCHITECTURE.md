# TeluAI Architecture Constitution

## Purpose

TeluAI is a Melimi-first language platform. The architecture must favor correctness, explicit authority, simple boundaries, and deterministic behavior over feature count.

## Non-negotiable rules

1. **One production entrypoint.** `app.server:app` is the production ASGI composition boundary.
2. **One application path per use case.** HTTP handlers and middleware must delegate to canonical application/domain services rather than reimplementing business logic.
3. **Frontend is a client.** UI code renders state, collects input, calls canonical APIs, and presents results. It is never a security or authorization boundary.
4. **Workspace authorization is server-side.** Data queries and resource access are scoped to the authenticated user and requested workspace before data reaches the UI.
5. **Main chat commands remain valid.** Explicit language-learning commands such as `/word` are part of the canonical chat-learning workflow unless a command is explicitly designated Lab-only.
6. **Melimi is native-first.** Telugu, Roman Telugu, and explicit Melimi requests use the native language path unless the user explicitly selects Standard Telugu.
7. **Standard Telugu is explicit.** Native Melimi knowledge must not be silently replaced with general/standard Telugu knowledge.
8. **Unknown language forms are never fabricated.** Unsupported words, derivations, and inflections remain unsupported until authoritative evidence exists.
9. **Authority is explicit.** Ordinary conversation, retrieval, and LLM output are advisory evidence; they cannot silently become Master language authority.
10. **Learning is explicit.** Promotion into authoritative language state requires the existing explicit teaching/review workflow.
11. **Deterministic language operations are local-first.** Lookup, normalization, validation, morphology, and other established language operations must not require an external LLM unless the operation genuinely needs generation.
12. **LLMs are adapters.** Provider-specific SDK/API details stay behind provider/application boundaries and never become scattered through UI or domain logic.
13. **Persistence has a boundary.** Application/domain code should use repository/service interfaces rather than opening arbitrary database sessions throughout business logic.
14. **Errors are truthful.** Never manufacture success, progress, AI output, or integration status. Errors must preserve actionable cause information without exposing secrets.
15. **Async work is latest-safe.** A stale request must never overwrite newer state; cancellation, request identity, or equivalent protection is required where concurrent work can race.
16. **Tests specify behavior.** Prefer behavioral contracts over brittle implementation/string-presence tests.
17. **No dead UI.** Every visible action must work, be intentionally secondary, or be removed.
18. **No compatibility layer without an owner.** Temporary compatibility code must have a documented reason and removal condition.

## Layering

```text
Browser
  -> API / transport
  -> application services
  -> domain engines and policies
  -> infrastructure adapters
  -> persistence / external providers
```

### API / transport
Handles HTTP, authentication dependencies, serialization, streaming transport, and status codes.

### Application
Owns use-case orchestration: chat, workspace, learning, and other product workflows.

### Domain
Owns language rules, authority, morphology, routing policy, validation, and product invariants. Domain code should be deterministic where possible.

### Infrastructure
Owns SQLAlchemy, external LLM providers, GitHub synchronization, email, and other external systems.

## Migration policy

Legacy code is migrated incrementally. Each migration must:

1. preserve an existing behavioral contract;
2. add or update regression coverage;
3. move ownership to the correct layer;
4. remove the old implementation after the new path is verified.

Do not perform broad rewrites without a tested migration seam.
