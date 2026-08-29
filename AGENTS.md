# TeluAI Agent Constitution

This file is the repository-level contract for any coding agent working on TeluAI. Read it before changing code.

## 1. Product

TeluAI is currently **one Telugu-first AI conversation product**.

- Natural Telugu conversation is the default.
- Telugu, Roman Telugu, and mixed Telugu should be understood naturally.
- Do not turn ordinary conversation into dictionary/grammar/research analysis unless explicitly requested.
- Coding and unrelated non-Telugu conversation must not silently become Melimi learning.
- **Melimi Telugu Lab/workspace is deferred**. Do not restore its routes, UI, APIs, or tests into the current product.
- Keep the UI focused on the primary conversation task.

## 2. Melimi learning scopes

Keep these concepts separate:

```text
MASTER AUTHORITY
  authoritative language truth

GLOBAL LEARNING
  explicit teaching by owner / approved admin

USER LEARNING
  explicit teaching by one ordinary user, private to that user
```

Rules:

- Owner explicit Melimi teaching → GLOBAL.
- Approved admin explicit Melimi teaching → GLOBAL.
- Ordinary user explicit Melimi teaching → USER:<id> only.
- User A must never receive User B's private learning.
- AI output, guesses, retrieved text, and ordinary observations are **not authority**.
- Conversational learning must preserve provenance, scope, status, and evidence.
- Unknown words/forms must remain unknown; never fabricate a Melimi form.
- Preserve authoritative root-first morphology, productive rules, inflection, sandhi, and noun/verb distinctions already established by the project.

## 3. Canonical architecture

Prefer:

```text
Frontend
  → canonical transport
  → application/chat boundary
  → routing
  → deterministic/local language operations
  → optional LLM generation
  → validation/repair
  → persistence
  → response
```

- Frontend is a product shell, not a second backend.
- Business rules belong in domain/application/service layers.
- Maintain one source of truth for each business concept.
- Do not create parallel chat pipelines, duplicate routing, language detection, normalization, or persistence.
- External providers stay behind explicit boundaries.
- Local deterministic language behavior must remain usable without an LLM where promised.
- Production entrypoints must use the canonical ASGI application.
- Do not introduce compatibility layers unless necessary; document their removal condition.

## 4. Autonomous change protocol

For every development request:

```text
INSPECT
→ REPRODUCE
→ TRACE WORKFLOW
→ IDENTIFY ROOT CAUSE
→ DESIGN COHERENT FIX
→ IMPLEMENT
→ REGRESSION TEST
→ TARGETED VALIDATION
→ FULL VALIDATION
→ INSPECT DIFF
→ SEARCH STALE/OBSOLETE CONTRACTS
→ VALIDATE AGAIN
→ VERIFY GITHUB CI
→ SECOND GAP SWEEP
```

Before coding, inspect the current repository, relevant history, tests, configuration, deployment, and latest CI. Do not assume a test is correct merely because it is red: determine whether the implementation or the test contradicts the current product contract.

If a CI failure occurs, the agent should diagnose and fix it without waiting for the user to repeat "fix". Continue while RED when connected GitHub tooling permits it.

Never:

- weaken assertions merely to pass;
- add `xfail` to hide a defect;
- skip/disable CI;
- swallow errors to manufacture success;
- fake provider responses/results;
- resurrect obsolete product surfaces solely for stale tests;
- hard-code a result solely for one failing test.

## 5. Tests and CI

Final validation must use the complete suite, not only `--maxfail=1`.

When applicable verify:

- dependency consistency
- Python compilation
- JavaScript syntax
- canonical production import/composition
- repository hygiene
- full pytest suite
- offline language evaluation
- architecture contracts
- security-sensitive behavior
- browser/E2E workflows
- production smoke behavior

Permanent behavioral contracts should cover:

- single Telugu chat product
- no current Lab surface/routes/workspace leakage
- owner/admin global learning
- ordinary-user private learning
- no cross-user leakage
- no automatic authority promotion
- non-Telugu/coding traffic excluded from Melimi learning
- native/local lookup and morphology
- explicit teaching/provenance
- authentication/authorization
- streaming/persistence
- graceful external-provider failure
- frontend/backend transport boundary

## 6. Security and data safety

Treat conversation and user learning as private by default.

Audit relevant changes for authentication/authorization bypass, cross-user leakage, cross-scope leakage, XSS/unsafe HTML, SQL injection, path traversal, SSRF/command injection, malicious files, prompt injection through language evidence, secret exposure, and resource exhaustion.

For database changes inspect existing schema/data first. Preserve users, conversations, learned knowledge, master language data, transactions, rollback, idempotency, and test isolation. Never use destructive migrations merely to make tests easier.

## 7. UX, performance, and errors

Apply **elementary excellence**:

- primary task first
- minimal UI
- strong defaults
- truthful loading/success/failure states
- actionable errors
- responsive/accessibility basics
- no dead controls
- no fake progress

Optimize measured bottlenecks, not guesses.

Errors should distinguish validation, authentication, authorization, missing resources, provider failures/timeouts, persistence failures, and internal failures. Do not hide operationally important failures.

## 8. Git and completion

Use focused commits and PRs for substantial changes. Never commit secrets, caches, generated artifacts, or debugging leftovers.

**CI GREEN is necessary, not sufficient.** A change is DONE only when applicable evidence exists for implementation, behavior, regression coverage, architecture, security, UX, production composition, complete CI, and production smoke verification when deployment is involved.

If something was not verified, report exactly:

`NOT VERIFIED`

Never claim that code was changed, tested, deployed, or verified without tool evidence.
