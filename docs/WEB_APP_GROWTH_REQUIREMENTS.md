# TeluAI — Complete Web App Growth Requirements

This is the production-growth checklist for the current PostgreSQL-backed TeluAI architecture. It separates what the product needs from what is already implemented.

## 1. Product foundation

- [x] Guest-first usage without mandatory email login.
- [x] Username/password guest accounts.
- [x] Email registration and login.
- [x] Profile and credential management.
- [x] Password recovery by verification code.
- [x] Conversation history and reopening.
- [x] Persistent PostgreSQL data model.
- [x] Melimi Language Space as the authoritative language subject.
- [x] Explicit `/word` and `/content` commands for direct language entry.
- [ ] Clear separation between ordinary chat, personal memory, and language knowledge in every code path.

## 2. Conversational AI

- [x] Conversation state and intent analysis.
- [x] Short-message/context handling.
- [x] Local deterministic answers where appropriate.
- [x] Melimi language retrieval and lexical policy.
- [x] Bounded Melimi repair/validation.
- [ ] Context-aware response caching; cached answers must never cross conversation contexts.
- [ ] Streaming responses for better perceived latency.
- [ ] User-visible retry for transient AI failures.
- [ ] Model fallback/health policy when the primary provider is unavailable.
- [ ] Automated conversational regression set covering follow-ups and corrections.

## 3. Language Space

- [x] PostgreSQL-backed vocabulary and documents.
- [x] Direct MASTER vocabulary registration.
- [x] Direct MASTER content registration.
- [x] Versioning and index invalidation.
- [x] Admin edit/delete capabilities.
- [x] Search and category-oriented Language Space UI.
- [ ] Full-text search ranking and phrase retrieval.
- [ ] Duplicate/near-duplicate detection.
- [ ] Provenance for every entry (actor, timestamp, source, version).
- [ ] Safe rollback/version history for accidental direct edits.
- [ ] Language-space import/export backup workflow.

## 4. Accounts and security

- [x] HttpOnly session cookie.
- [x] Secure cookie support on Render.
- [x] Role-based admin/owner endpoints.
- [x] Owner protection from self-demotion/deletion.
- [x] Password reset session/token flow.
- [ ] Replace email-only owner bootstrap with a one-time secret/bootstrap token.
- [ ] Remove automatic owner promotion during every application startup.
- [ ] Rate limiting for login, guest creation, password reset, and chat.
- [ ] CSRF protection for state-changing browser requests if cross-site access is ever enabled.
- [ ] Security headers (CSP, HSTS, frame policy, referrer policy, content type policy).
- [ ] Session revocation UI and active-session visibility.
- [ ] Audit sensitive account changes consistently.

## 5. API and backend quality

- [x] Pydantic validation for core request models.
- [x] Ownership checks for conversations.
- [x] Admin/owner dependency checks.
- [x] Explicit HTTP errors for common failures.
- [ ] Replace broad `dict` payloads with typed request/response models.
- [ ] Centralized exception handling and structured error codes.
- [ ] Request correlation IDs.
- [ ] Request size/rate limits at the application boundary.
- [ ] Database transaction boundaries and rollback-safe service functions.
- [ ] Database connection-pool tuning for Render.
- [ ] Background jobs for slow/non-interactive work.

## 6. Database and data integrity

- [x] PostgreSQL production support.
- [x] Startup migration mechanism.
- [x] Knowledge versioning.
- [x] Conversation ownership checks.
- [ ] Real migration history instead of relying only on startup patch logic.
- [ ] Foreign-key/index audit for all high-volume tables.
- [ ] Unique constraints for language mappings and session identifiers.
- [ ] Backup/restore procedure tested against production-shaped data.
- [ ] Retention/cleanup policy for expired sessions, reset tokens, cache, and audit records.

## 7. Frontend / UX

- [x] Responsive desktop/mobile UI.
- [x] Guest/profile account menu.
- [x] Settings with theme, text size, density, response length, and memory controls.
- [x] Mobile navigation drawer.
- [x] Conversation history modal.
- [x] Profile modal.
- [x] Admin console separated into focused sections.
- [ ] Eliminate duplicate event handlers and legacy navigation code.
- [ ] Add visible loading states to every async action.
- [ ] Add retry actions to failed history/settings/admin requests.
- [ ] Improve mobile drawer width, spacing, and touch targets based on real devices.
- [ ] Keyboard/focus accessibility audit.
- [ ] Screen-reader labels and dialog semantics audit.
- [ ] Offline/network-loss messaging.

## 8. Performance

- [x] Context-length limits.
- [x] Response token limits.
- [x] Knowledge version-aware cache keys.
- [ ] Include conversation context in cache eligibility/keying.
- [ ] Avoid repeated full index reloads when multiple writes occur together.
- [ ] Add database indexes based on real query plans.
- [ ] Compress/stream large language documents.
- [ ] Frontend asset caching/versioning.

## 9. Observability and operations

- [x] Basic `/health` endpoint.
- [x] Usage/error recording.
- [x] Admin audit log.
- [ ] Health endpoint must verify database connectivity rather than infer it from `DATABASE_URL`.
- [ ] Provider health/latency metrics.
- [ ] Structured JSON application logs.
- [ ] Error-rate and latency dashboards.
- [ ] Render deploy smoke test after every production deployment.
- [ ] Alerting for repeated startup failures and provider failures.

## 10. Testing and CI/CD

- [x] Python compilation in CI.
- [x] Dependency consistency check.
- [x] Frontend JavaScript syntax check.
- [x] Automated pytest suite.
- [ ] Fresh green CI run on the current `main` after architecture changes.
- [ ] API integration tests against PostgreSQL.
- [ ] Browser/E2E tests for guest → chat → history → profile → settings.
- [ ] Admin authorization regression tests.
- [ ] Language-space direct-entry regression tests.
- [ ] Render production smoke test.
- [ ] Dependency vulnerability scanning.

## 11. Repository hygiene

- [ ] Remove committed `__pycache__` / `.pyc` artifacts.
- [ ] Remove obsolete duplicated `app/app` package.
- [ ] Remove stale release notes and documentation that describe superseded architecture.
- [ ] Keep one authoritative dependency manifest.
- [ ] Keep README aligned with the PostgreSQL/direct-entry architecture.
- [ ] Keep production configuration examples aligned with Render.

## 12. Release gates

A release should not be called production-ready until all of these are green:

1. `python -m compileall -q app tests`
2. `pip check`
3. frontend JavaScript syntax check
4. full pytest suite
5. API integration tests
6. guest/login/profile/history/settings smoke flow
7. admin authorization smoke flow
8. `/word` direct-entry retrieval test
9. `/content` direct-entry retrieval test
10. Render deployment reaches `Application startup complete.`
11. `/health` reports a live database connection
12. no Critical/High security findings remain

## Current priority order

### P0 — before calling production stable
- Fix all startup/import failures.
- Make main UI event initialization fail-safe.
- Remove automatic owner promotion.
- Secure owner bootstrap.
- Prevent context-incorrect cache hits.
- Get CI green.
- Verify Render startup and health.

### P1 — next growth phase
- PostgreSQL integration/E2E tests.
- Rate limiting and security headers.
- Better Language Space search/provenance/versioning.
- Streaming/retry/fallback AI behavior.
- Mobile accessibility and async-state polish.

### P2 — scale and maturity
- Background jobs.
- Observability dashboards/alerts.
- Backups and tested recovery.
- Dependency/security automation.
- Advanced linguistic regression and naturalness evaluation.
