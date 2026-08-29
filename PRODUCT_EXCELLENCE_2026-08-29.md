# Product Excellence Pass — 2026-08-29

This pass makes the main TeluAI workspace materially more focused without changing the backend contract.

## User-facing changes

- Reworked the welcome workspace around four task-oriented actions instead of four architecture cards.
- Added a compact Telugu-first status cue and privacy/memory guidance.
- Added a persistent desktop sidebar collapse control so the conversation can own more of the viewport.
- Added Focus mode for distraction-free conversation; it removes secondary navigation without changing chat behavior.
- Improved suggestion cards with clear action + outcome descriptions.
- Added keyboard/focus affordances and tighter spacing across the primary workspace.
- Kept mobile layout adaptive rather than shrinking the desktop layout.

## Engineering principle

The change is deliberately additive at the presentation boundary: existing chat IDs, API routes, authentication, history, settings, streaming and message actions remain unchanged.
