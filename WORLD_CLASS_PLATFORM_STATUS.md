# TeluAI World-Class Platform — Engineering Status

## Baseline audited

The existing FastAPI + PostgreSQL + Groq + deterministic Melimi foundation is retained.
The current runtime already contains several of the target abstractions: a canonical chat service used by `ChatOverrideMiddleware`, an LLM provider protocol, version-keyed Melimi indexes, typed linguistic transformation contracts, an evidence/ranking layer, learning review, and an offline evaluation command.

## Implemented in this phase

### 1. Authority-aware evidence

`app/retrieval/evidence.py` now treats authority and confidence as separate concepts. `MASTER` is the only runtime-authoritative evidence tier. Evidence records expose source identity, source type, provenance, knowledge version, lexical/semantic/grammatical/contextual scores, freshness, and an explanation payload.

Weak evidence therefore cannot become authority merely because its confidence is high.

### 2. Explicit insufficient-evidence state

Evidence ranking returns an explicit insufficient state when no published `MASTER` evidence satisfies the query. The language engine can therefore distinguish missing authority from a valid answer.

### 3. Scientific offline evaluation expansion

`app/eval.py` now measures deterministic intent, language detection, routing, unseen morphology, unsupported-word preservation, and authority adherence. Metrics without deterministic ground truth remain `null`; no performance number is fabricated.

The corpus includes unseen noun inflection, case realization, unknown-word preservation, and authority adversarial cases.

### 4. Prompt artifacts

`app/prompt_registry.py` defines stable prompt IDs, versions, purpose, input/output contracts, language policy, safety policy, and evidence policy. The canonical chat preparation service now records the prompt artifact metadata and current language knowledge version in its planning metadata.

## Existing architecture confirmed during audit

- `app/llm/provider.py` already provides the provider protocol and Groq adapter.
- `app/melimi/root_morphology.py` and registry/index caches are keyed by the shared language-space version.
- `app/melimi/engine.py` already feeds ranked evidence and an explicit insufficient-evidence message into the Melimi context.
- Learning approval already records reviewer identity and creates a `KnowledgeVersion` for root approval.
- The deterministic firewall remains the final authority for supported Melimi transformations.

## Remaining principal-engineering work

1. Remove or isolate the legacy chat orchestration in `app/main.py`; keep one canonical application service without changing public API behavior.
2. Remove migration-time runtime wiring. Database migration must remain database migration; application composition belongs to application startup/factory code.
3. Audit and retire the unused `app/db/*` async PostgreSQL subsystem if repository-wide usage remains zero. It duplicates the existing `app/database.py` authority/cache/learning model.
4. Make publication, provenance, audit event, and knowledge-version update one explicit transaction boundary for every language mutation path, not only the main root approval path.
5. Persist structured response provenance (request ID, prompt version, knowledge version, evidence IDs, intent, validation result, and stage timings) without storing secrets or unnecessary user content.
6. Expand adversarial security and language tests, especially prompt injection inside retrieved/uploaded language content and stale-version/concurrent publication cases.
7. Split fast CI checks from deeper evaluation and add migration/schema validation.
8. Add provider-backed evaluation for contextual accuracy, hallucination rate, latency, and token efficiency. Offline CI must continue to avoid real provider calls.

## Release rule

This branch is **not a deployment/release candidate**. A green CI result only proves the implemented changes are internally consistent; the remaining architecture, provenance, security, and evaluation stages must be completed and reviewed before deployment.
