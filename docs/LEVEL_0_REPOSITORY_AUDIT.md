# Level 0 — Repository Stabilization Audit

Date: 2026-08-22

## Decision

Preserve the current Language Space authority, avoid duplicate language/database infrastructure, and move to the canonical chat application boundary.

## Findings

- Current Melimi indexes are version-aware and tied to shared Language Space authority.
- Legacy cache/reference work was not imported wholesale.
- Migration code remains a startup composition boundary.
- Canonical chat consolidation is the next architecture task.
- CI retains dependency, compile, frontend syntax, hygiene, full pytest, and offline evaluation gates.

## Level 1 gate

Identify every chat entry point, select one canonical application service, preserve public API behavior, move orchestration out of HTTP implementation, add contract tests, and verify CI.
