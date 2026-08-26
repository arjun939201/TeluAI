# Level 1 — One TeluAI Core / Chat Orchestration

## Canonical path

```text
HTTP transport → ChatOverrideMiddleware → prepare_chat_turn()
→ app.chat.service.prepare_prompt() → Melimi context → LLM provider
→ persistence / transport
```

## Verified design

- JSON and streaming use the same application preparation boundary.
- Regeneration and branching reuse the streaming path.
- Middleware is a compatibility/transport layer, not a second prompt engine.
- Message editing is persistence-only.
- Contract tests cover the application boundary and transport delegation.

## Gate

After CI is green, audit legacy `/chat` orchestration in `app/main.py` and remove only code proven shadowed by the explicit ASGI transport boundary.
