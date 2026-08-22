# Level 1 — One TeluAI Core / Chat Orchestration

## Current status

The canonical chat application boundary is established in `app/chat/application.py`.

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
- Contract tests cover the application boundary and middleware delegation.
- Runtime transport tests cover JSON completion and streaming responses with a mocked provider.
- Message editing is verified as persistence-only and does not invoke AI preparation.
- Regeneration is verified to branch the conversation and route the resulting turn through the streaming handler.
- CI #431 passed the complete test suite and offline language evaluation for the canonical transport boundary.

## Remaining Level 1 work

1. Run and verify CI for the latest runtime transport tests.
2. Audit the legacy `/chat` handlers in `app/main.py`; keep them only while compatibility requires them and document them as shadowed by the explicit ASGI transport boundary.
3. Remove legacy orchestration only after the current transport tests prove equivalent behavior and the frontend/deployment path has been verified.
4. Publish a final Level 1 architecture audit and then advance to Level 2.

## Architectural rule

There must be one conversation orchestration path. Transport code may perform authentication, rate limiting, request decoding, and response formatting, but it must not independently construct conversation state, linguistic context, prompts, or AI decisions.
