# TeluAI Architecture Audit — 2026-08-18

## Scope

Audit of the `main` branch at commit `43a3e7f4771e6a4a33c9555fc965f14c473a1a99` before the next engineering phase. The audit follows the existing repository architecture and preserves the current FastAPI/PostgreSQL/Groq/Melimi foundation.

## Current architecture map

```text
Frontend (static/)
        |
        v
FastAPI app.main
        |
        +--> auth / account / admin / uploads / GitHub routes
        |
        +--> /chat route (legacy orchestration)
        |
        +--> lifespan -> migrations.run_migrations()
                         |
                         +--> installs ChatOverrideMiddleware
                         +--> installs chat-learning monkey patches
        |
        v
ChatOverrideMiddleware (runtime canonical for POST /chat)
        |
        +--> app.chat.service.prepare_prompt()
        |       +--> router
        |       +--> conversation state/intent/planner
        |       +--> linguistics
        |       +--> memory
        |       +--> Melimi engine
        |       +--> prompts
        |
        +--> direct Melimi lookup
        +--> Groq provider
        +--> deterministic repair
        +--> chat persistence

Language authority
        |
        +--> PostgreSQL MelimiRoot / Rule / Affix / Example / Document / KnowledgeEntry
        +--> KnowledgeVersion
        +--> LearningCandidate
        +--> Language Space admin views
        +--> runtime indexes/caches

Infrastructure
        +--> SQLAlchemy
        +--> Groq-compatible HTTP client
        +--> GitHub synchronization
        +--> in-process rate limiter
        +--> audit logging
```

## What is already good

- PostgreSQL is the production/runtime language store; SQLite is explicitly a local fallback.
- Language knowledge is versioned with `KnowledgeVersion`, and the recent universal-refresh regression test establishes the intended cross-worker cache behavior.
- Conversation state, intent inference, planning, bounded history, persistent memory, Melimi root-first morphology, deterministic repair, learning review, uploads, role authorization, audit logging, and security middleware already exist.
- The project explicitly rejects invented Melimi authority and treats uploaded/user language data as untrusted until review.
- CI is pinned to specific GitHub Action commits and runs dependency checks, compilation, frontend syntax checks, hygiene checks, and pytest.

## Findings

### P0 — Correctness / authority

1. **Approved learning is not consistently promoted to `MASTER`.** `review_candidate()` writes approved roots with status `APPROVED`, while runtime language accessors currently include every status except `REJECTED`. This creates an authority-state mismatch: `APPROVED` behaves as runtime authority even though the documented authority model says `MASTER` is the published state.
2. **Approved learning does not create a `KnowledgeVersion`.** This can leave knowledge-dependent response caches and process-local indexes unaware of a newly approved entry unless an unrelated refresh occurs.
3. **Reviewer identity is not persisted on `LearningCandidate`.** The API receives a reviewer id and audits it, but the candidate itself only stores `reviewed_at` and reviewer note embedded in JSON. This weakens provenance and reproducibility.
4. **Runtime cache invalidation must be version-keyed, not merely expose a version parameter.** The current root-morphology implementation accepts a version argument but the default cache key remains `None`, so the shared version does not actually invalidate that cache. Similar review is required for registry/index/firewall/retrieval caches.

### P1 — Architecture / maintainability

5. **There are two chat orchestration pipelines.** `app.main.chat()` contains a full chat implementation, while startup installs `ChatOverrideMiddleware`, which intercepts `/chat`, `/chat/stream`, message editing, and branching and uses `app.chat.service`. The middleware therefore makes the main `/chat` implementation effectively shadowed in normal runtime. This is hidden coupling and duplicated business logic.
6. **`migrations.py` performs application wiring.** It imports `app.main`, installs middleware, and installs monkey patches during startup. Database migration/bootstrap should not be the mechanism that assembles the request pipeline.
7. **`chat_learning_runtime.py` monkey-patches `local_answer.answer` and `prompts.build_prompt`.** This is powerful compatibility code but creates implicit global state and makes import order part of application behavior.
8. **`database.py` is an oversized infrastructure/domain mixture.** It contains models, schema upgrades, seed import, language ingestion, authentication persistence, sessions, conversations, learning approval, memory persistence, cache operations, audit logging, and user administration.
9. **`KnowledgeEntry` and the typed Melimi tables overlap.** This is useful for compatibility, but the authority boundary and ownership of each record type should be explicit.
10. **The LLM boundary is provider-specific.** `app.groq_client` is already resilient, but the application directly imports Groq functions instead of depending on a small provider protocol.

### P1 — Evidence / linguistic reliability

11. Retrieval currently ranks lexical overlap but has no explicit evidence object containing authority, status, version, provenance, and confidence.
12. `build_language_engine_context()` constructs a large textual authority block and asks the LLM to follow it, but the response pipeline does not expose a structured evidence set or an explicit `INSUFFICIENT_LANGUAGE_EVIDENCE` state.
13. The deterministic firewall is strong and root-first, but grammatical features are still represented mostly as operation strings rather than a typed morphological feature model.
14. Intent routing is mostly deterministic and intentionally lightweight, which is good, but language-learning, translation, contribution, memory, and administrative intent categories are not represented as a single typed domain model.

### P2 — Data / performance

15. Several language accessors call `init_db()` from runtime retrieval paths. That can perform schema/bootstrap work during ordinary requests and is unnecessary after application startup.
16. The in-process sliding-window limiter is correct for one process but not a distributed limiter for multiple Render workers/instances.
17. Some database query patterns are bounded but still load large collections for in-memory filtering (for example parts of Language Space). More filtering/pagination can move to PostgreSQL when scale requires it.
18. Response cache correctness is partly handled through knowledge version and disabled for personalized new-chat cases, which is good; the cache contract should become explicit and tested against every user-specific dimension.

### P2 — Observability / evaluation

19. Usage data captures model/tokens/latency, but the full AI decision provenance requested for reproducibility is not yet persisted: request id, knowledge version, evidence ids, prompt version, plan, validation/transformation result, and stage latency.
20. Prompt versions are not first-class identifiers; prompts are currently assembled from code strings.
21. The repository has many regression/unit tests but no project-level language evaluation command or curated metric report covering intent, retrieval, Melimi correctness, unsupported invention, and contextual behavior.

### Security review notes

- Server-side role dependencies are used for administrative routes.
- Session cookies are HttpOnly and SameSite-controlled.
- Upload size/type/ZIP-member limits exist.
- User language contributions are routed to learning candidates rather than directly becoming MASTER.
- External/user language content must remain data, not executable instructions, when passed into retrieval or LLM prompts.
- The current audit does not justify introducing new security middleware without a concrete finding; the existing baseline should be preserved while adding targeted tests.

## Priority plan

### P0

1. Make published language authority state unambiguous: only `MASTER` is runtime-authoritative for Melimi mappings/rules unless a specific subsystem documents another state.
2. On approval/publication, atomically write the authoritative record and a `KnowledgeVersion`, with reviewer identity/provenance.
3. Make every language cache actually keyed by the shared knowledge version; add tests that mutate language data without calling `reload_*()`.

### P1

4. Establish one canonical chat application service and remove/shrink the shadow orchestration in `main.py`.
5. Replace migration-time middleware installation and monkey-patching with explicit application composition.
6. Introduce typed evidence contracts and evidence ranking while preserving the current retrieval engine.
7. Introduce an `LLMProvider` protocol with the existing Groq implementation as the first adapter and a deterministic/mock adapter for tests.
8. Add prompt identifiers/version metadata and structured pipeline telemetry.
9. Add a language evaluation corpus and offline evaluation command.

### P2

10. Split `database.py` by infrastructure responsibility only where real boundaries emerge.
11. Move Language Space filtering/pagination toward database-side queries where measurements show benefit.
12. Add distributed rate limiting only when multi-instance deployment requires it.
13. Improve frontend observability/loading/error UX without coupling it to internal language-engine modules.

## Non-goals

- No microservices.
- No Kubernetes.
- No Redis/vector database without measured need.
- No replacement of FastAPI, PostgreSQL, Groq, or the existing deterministic Melimi firewall merely for architectural fashion.
- No automatic promotion of model-generated language knowledge to MASTER.
- No wholesale rewrite of the existing language corpus.

## Engineering rule

Every refactor should preserve a working vertical slice and add a regression test before changing the next boundary. Language authority is treated as data with provenance and version, not as a prompt convention.
