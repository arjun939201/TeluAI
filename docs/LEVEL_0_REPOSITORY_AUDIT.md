# Level 0 — Repository Stabilization Audit

Date: 2026-08-22

## Baseline

`main` is the production integration branch. The repository currently has a FastAPI + PostgreSQL + Groq foundation, a shared Language Space, version-keyed Melimi indexes, typed linguistic contracts, evidence ranking, learning/review infrastructure, and deterministic offline evaluation.

## Findings

### 1. Obsolete cache-refresh PR

PR #5 (`agent/strong-telugu-language-system`) was a draft based on an older `main` and is not the current integration path. Its cache-refresh concern is already represented by the current version-keyed index implementation: `app/melimi/index.py` resolves the shared language-space version before using the versioned index cache.

The PR has been archived/closed rather than merged wholesale, preventing old architecture and reference-corpus changes from re-entering `main` without an explicit authority review.

### 2. Current Melimi index

`app/melimi/index.py` uses `build_index(version)` and an `lru_cache` keyed by the resolved Language Space version. This gives the runtime a version-aware cache boundary rather than a process-lifetime snapshot.

### 3. Database authority

`app/db/*` was not found on the current `main` tree through the repository contents API. The current runtime imports database authority from `app.database` and language-specific persistence through `app.melimi.db_subject`.

This item is therefore downgraded from an active duplicate-subsystem task to a verification item: continue searching runtime/deployment references before declaring the architecture fully consolidated.

### 4. Migration boundary

`app/migrations.py` is currently limited to schema creation/index/column migrations and does not contain AI or route composition. Application startup invokes migrations from the FastAPI lifespan. This is acceptable as an explicit startup composition boundary for now, but migration tests should be strengthened before production release.

### 5. Canonical chat consolidation

`app/main.py` still contains substantial HTTP/authentication/application concerns and invokes the language engine and conversation services. The repository status correctly identifies canonical chat-service consolidation as remaining work. This is the next major architecture task; do not attempt a risky rewrite during Level 0.

### 6. CI

The current CI workflow runs dependency consistency, Python compilation, frontend syntax validation, repository hygiene, the full pytest suite, and offline language evaluation. Provider-backed evaluation remains intentionally separate from offline CI.

## Level 0 decision

- Preserve current `main`.
- Do not merge obsolete PR #5.
- Do not import its large reference corpus wholesale.
- Preserve the current version-aware cache architecture.
- Move to Level 1: canonical TeluAI application/chat orchestration.

## Next engineering gate

Before Level 1 is merged:

1. Identify every chat entry point and caller.
2. Select one canonical application service.
3. Preserve public API behavior.
4. Move orchestration out of HTTP route implementation where appropriate.
5. Add contract tests for Main Chat.
6. Verify CI remains green.

## Non-goals for Level 0

- No new AI engine.
- No new database.
- No new vocabulary dictionary.
- No wholesale rewrite.
- No automatic promotion of language data.
