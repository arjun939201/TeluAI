# TeluAI Engineering Audit — 2026-08-29

## Initial findings

The current repository has a strong backend foundation, extensive regression coverage, explicit workspace boundaries, a provider adapter, and a security baseline. The main reliability risk is not missing infrastructure; it is duplicated runtime paths and inconsistent production composition.

### Critical findings

1. **Production entrypoints are inconsistent.** Render starts `app.lab_server:app`, while Docker starts `app.main:app`. `app.main` does not install the canonical chat/workspace composition used by `app.server`.
2. **The frontend contains a compatibility fetch bridge that converts `/chat/stream` into a normal `/chat` request.** This defeats the real SSE streaming implementation and creates a false streaming experience.
3. **The frontend's workspace injection expects a `.nav` element that the current main shell does not contain.** The main page already contains a direct Lab link, so this enhancement is ineffective/dead.
4. **The learning candidate lifecycle is still semantically ambiguous.** Approved candidates create authoritative `MASTER` language records and a knowledge version, but the candidate itself remains `APPROVED`. This should be treated as an explicit audit/workflow state rather than being confused with publication authority.
5. **The repository contains multiple chat orchestration layers.** `app.main` retains a legacy `/chat` implementation while `app.chat.middleware` is the normal canonical transport when `app.server` is composed. This is a maintainability risk and should be consolidated after preserving a tested vertical slice.
6. **The security CSP contains hard-coded external deployment origins.** This should become configuration-driven rather than coupling the security policy to known domains.

## First repair wave

- Make `app.server:app` the single documented production ASGI composition for both Docker and Render.
- Remove the frontend fake-streaming compatibility bridge; use the existing real `/chat/stream` transport.
- Remove the ineffective main-workspace DOM injection and keep workspace routing explicit.
- Add regression tests covering canonical production composition and the absence of the fake streaming bridge.

## Next audit targets

- consolidate legacy `/chat` orchestration behind the canonical application service
- make language publication state explicit and transactional
- audit all knowledge caches for version-key correctness
- make CSP deployment origins configurable
- add structured request/pipeline provenance and evaluation metrics
- measure database/runtime performance before splitting `database.py`

No microservices, Redis, vector database, Kubernetes, or wholesale rewrite is justified by the current evidence.
