# Level 1 — One TeluAI Core / Chat Orchestration

## Current status

The canonical chat application boundary is now established in `app/chat/application.py`.

### Canonical path

```text
HTTP transport
    ↓
ChatOverrideMiddleware
    ↓
prepare_chat_turn()
    ↓
app.chat.service.prepare_prompt()
    ↓
Melimi language context (when applicable)
    ↓
LLM provider
    ↓
response persistence / transport
```

## Verified

- Main frontend chat compatibility is preserved through the explicit ASGI composition in `app/server.py`.
- JSON chat preparation uses `prepare_chat_turn()`.
- Streaming chat preparation uses the same application boundary.
- Regeneration/branching reuses the same preparation path before streaming.
- The middleware contains a compatibility `_prepare()` shim rather than a second prompt-building implementation.
- Contract tests cover both the application boundary and middleware delegation.
- CI #428 passed the complete test suite and offline language evaluation for the corrected contract.

## Remaining Level 1 work

1. Add production-style JSON chat integration coverage.
2. Add streaming chat integration coverage.
3. Add regeneration/branch integration coverage.
4. Verify message editing remains persistence-only and does not create a second AI orchestration path.
5. Audit the legacy `/chat` handlers in `app/main.py`; keep them only while compatibility requires them and document them as shadowed by the explicit ASGI transport boundary.
6. Remove legacy orchestration only after integration tests prove equivalent behavior.
7. Publish a final Level 1 architecture audit and then advance to Level 2.

## Architectural rule

There must be one conversation orchestration path. Transport code may perform authentication, rate limiting, request decoding, and response formatting, but it must not independently construct conversation state, linguistic context, prompts, or AI decisions.
