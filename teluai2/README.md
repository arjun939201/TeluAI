# TeluAI 2

TeluAI 2 is a Melimi-first Telugu language platform. The existing application remains the migration/reference source while this package establishes clean domain boundaries for the rewrite.

## Core principle

**AI may discover, analyze, propose, and explain. Evidence establishes. Melimi-aware review governs. Melimi Core remembers. TeluAI uses.**

## Boundaries

- `domain/` — pure language and governance models/rules; no web or provider dependencies.
- `application/` — use cases and ports; orchestrates work without knowing infrastructure.
- `infrastructure/` — database, search, and AI-provider adapters.
- `api/` — HTTP boundary only.

## Knowledge lifecycle

`DISCOVERED → CANDIDATE → UNDER_REVIEW → ACCEPTED / REJECTED / DISPUTED`

Only accepted knowledge enters the authoritative runtime set. AI confidence never equals language authority.

## Rewrite policy

This foundation is intentionally additive on `teluai-2-rebuild`. Existing validated Melimi knowledge will be migrated through explicit adapters and checks rather than copied blindly.
